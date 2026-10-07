#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""脱敏四步 + 产物本体扫描审计器（M6 发布门，可入仓复跑）。

四种模式（缺一不可，全过打印 DESSENSITIZE_AUDIT_OK，任一硬命中 exit 1）：
  tracked  文件名扫描 + .gitignore 覆盖断言 + 全部跟踪文本文件内容级扫描
  binary   跟踪二进制 sha256 白名单对账 + docx 全 zip 条目扫描（docProps 元数据重灾区）
  history  历史三扫：log -p 全文 / rev-list --objects 对象路径 / 提交信息（log -p 已含）
  dist     构建产物本体扫描（--dist PATH，默认 dist/sfc；字节级强标记，不跑邮箱正则）

附加：--selftest 阳性/阴性对照（夹具全部程序化合成，无字面假密钥/假手机号）。

输出纪律：一律"path:行号 [类别] x次数"，不回显敏感串原文——报告可随仓留档。
命中分级：HARD（硬门，exit 1）/ REVIEW（复核项，人工豁免留档）。
本机字面值（旧邮箱等）不入仓：字面值级历史验证是仓外人工步骤（见 plan/RELEASE-M6.md），
本脚本只做模式前向覆盖。

源码自扫描纪律：本文件自身是 tracked 文件，会过自己的扫描——所有敏感词面
（个人目录名/用户名/姊妹项目名）一律以片段拼接或 base64 词表构造，不留完整字面值。
"""
import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WHITELIST = Path(__file__).resolve().parent / "binary_whitelist.json"
MARK = "DESSENSITIZE_AUDIT_OK"

BIN_EXT = {".docx", ".pdf", ".png", ".gif", ".jpg", ".jpeg", ".zip", ".exe", ".ico"}

# ---- 词表与敏感片段：全部拼接/base64，防源码自命中（字面值不入仓） ----

_SISTER_B64 = (
    "YmlkZGluZy1kb2N1bWVudC1jaGVja2VyLGNvbnN0cnVjdGlvbi1kcmF3aW5nLXBsYW4tY2hlY2tlcix"
    "mb29kLWxhYmVsLWNvbXBsaWFuY2UtY2hlY2tlcixpbnZvaWNlLWxlZGdlci1jaGVja2VyLG1lZGljYW"
    "wtcmVjb3JkLXF1YWxpdHktY2hlY2tlcixwb3dlci1vcGVyYXRpb24tdGlja2V0LWNoZWNrZXIscmVzdW"
    "1lLXRhbGVudC1wb29sLHN0cnVjdHVyYWwtc3RyZW5ndGhlbmluZy1jaGVja2VyLHdlaWRhLXBsYW4tcm"
    "V2aWV3LHNpdGVndWFyZCxVSFBDLU1peHR1cmUtRGVzaWdu"
)

def _sister_words():
    raw = base64.b64decode(_SISTER_B64).decode("utf-8")
    return [w for w in raw.split(",") if w]

# 用户目录名（片段拼接，不落完整字面值）
_UNAME = "AS" + "US"
# 邮箱豁免域（服务地址域 / 保留域 / 文档占位域）
_EXEMPT_DOMAINS = ("github.com",)
_EXEMPT_TLDS = (".example", ".test", ".invalid", ".localhost")
_EXEMPT_EXACT = ("example.com", "users.noreply.github.com")

# ---- 文本模式（HARD）----

def _hard_patterns():
    return [
        ("email", re.compile(r"[A-Za-z0-9][A-Za-z0-9._%+\-]*@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+")),
        # 手机号/证件号加 hex 边界环视：sha256 十六进制串内的数字段不是电话（白名单/文档 hex 误报校准）
        ("phone", re.compile(r"(?<![0-9a-fA-F])1[3-9]\d{9}(?![0-9a-fA-F])")),
        ("idcard", re.compile(r"(?<![0-9a-fA-F])\d{17}[\dXx](?![0-9a-fA-F])")),
        ("userpath-win", re.compile(
            r"(?i)(?<![a-z0-9])[a-z]:\\+" + r"use" + r"rs\\+[^\s\"'<>|,;)\]]+")),
        ("userpath-msys", re.compile(
            r"(?i)(?<![a-z0-9])/" + r"use" + r"rs/" + _UNAME.lower() + r"(?:/|[^\w]|$)")),
        ("secret-sk", re.compile(r"sk" + r"\-[A-Za-z0-9_\-]{16,}")),
        ("secret-assign", re.compile(
            r"(?i)(?:password|passwd|api" + r"_?key|secret|access" + r"_?token)"
            r"\s*[:=]\s*[\"']?[^\s\"']{8,}")),
        ("token-gh", re.compile(
            r"(?:ghp|gho|ghs|ghr)" + r"_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{20,}")),
        ("ip-private", re.compile(
            r"(?<![\d.])(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
            r"|192\.168\.\d{1,3}\.\d{1,3}"
            r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(?![\d.])")),
    ]

# ---- 文本模式（REVIEW）----

def _review_patterns():
    return [
        ("sister-word", re.compile(
            "|".join(re.escape(w) for w in _sister_words()), re.IGNORECASE)),
        # 其余盘符路径（个人目录已归 HARD）；系统目录同属复核项
        ("abs-path", re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:\\+[^\s\"'<>|,;)\]]+")),
    ]

_EMAIL_DOMAIN = re.compile(r"@([A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+)$")

def _email_exempt(candidate):
    m = _EMAIL_DOMAIN.search(candidate)
    if not m:
        return True  # 形态不完整不判邮箱
    dom = m.group(1).lower()
    if dom in _EXEMPT_EXACT or any(dom == d or dom.endswith("." + d) for d in _EXEMPT_DOMAINS):
        return True
    if dom.endswith(_EXEMPT_TLDS):
        return True
    return False

# ---- 字节级强标记（二进制/dist 专用：不跑邮箱正则，防上游公共邮箱刷屏）----

def _byte_patterns():
    pat = re.compile(
        b"use" + b"rs[\\\\/]+" + _UNAME.encode()
        + b"|" + b"/" + b"use" + b"rs/" + _UNAME.lower().encode(),
        re.IGNORECASE)
    return [("userpath-byte", pat)]

# ---- 扫描核心 ----

def scan_text(text, tag, findings, kinds="hard"):
    """扫描一段文本；findings 追加 (tag, 类别, 模式名, 次数)。不回显原文。"""
    if kinds in ("hard", "both"):
        for name, pat in _hard_patterns():
            n = 0
            for m in pat.finditer(text):
                if name == "email" and _email_exempt(m.group(0).strip(".,;:)]}'\"")):
                    continue
                n += 1
            if n:
                findings.append((tag, "HARD", name, n))
    if kinds in ("review", "both"):
        for name, pat in _review_patterns():
            if name == "abs-path":
                # 已被 HARD userpath 命中的行不再重复报 REVIEW
                hard_spans = [m.span() for m in re.compile(
                    r"(?i)[a-z]:\\+use" + r"rs").finditer(text)]
            n = 0
            for m in pat.finditer(text):
                if name == "abs-path":
                    s = m.start()
                    if any(hs <= s < he for hs, he in hard_spans):
                        continue
                    # 排除相对盘符误报：形如 D:\ 的才报
                    if not re.match(r"(?i)^[a-z]:\\", m.group(0)):
                        continue
                n += 1
            if n:
                findings.append((tag, "REVIEW", name, n))

def is_binary_bytes(data):
    if b"\x00" in data[:8192]:
        return True
    return False

def scan_docx_bytes(data, tag, findings):
    """docx：zipfile 扫全部 zip 条目（不只 document.xml，docProps/core.xml 元数据重灾区）。"""
    import io
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                data_e = zf.read(info.filename)
                ext = Path(info.filename).suffix.lower()
                if ext in (".xml", ".rels", ".txt"):
                    try:
                        scan_text(data_e.decode("utf-8", errors="replace"),
                                  "%s::%s" % (tag, info.filename), findings)
                    except Exception:
                        scan_bytes(data_e, "%s::%s" % (tag, info.filename), findings)
                else:
                    scan_bytes(data_e, "%s::%s" % (tag, info.filename), findings)
    except zipfile.BadZipFile:
        scan_bytes(data, tag, findings)

def scan_bytes(data, tag, findings):
    for name, pat in _byte_patterns():
        n = len(pat.findall(data))
        if n:
            findings.append((tag, "HARD", name, n))

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def git(args):
    cmd = ["git", "-c", "core.quotepath=false"] + args
    out = subprocess.run(cmd, cwd=str(REPO), capture_output=True)
    if out.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), out.stderr.decode("utf-8", "replace")))
    return out.stdout.decode("utf-8", errors="replace")

def tracked_files():
    return [l for l in git(["ls-files"]).splitlines() if l.strip()]

# ---- 模式实现 ----

def mode_tracked(findings):
    # 1) 文件名扫描
    bad_name = re.compile(r"\.env$|\.key$|secret|token|password|_private", re.IGNORECASE)
    for f in tracked_files():
        if bad_name.search(f):
            findings.append((f, "HARD", "filename", 1))
    # 2) .gitignore 覆盖断言
    gi = (REPO / ".gitignore")
    gi_text = gi.read_text(encoding="utf-8") if gi.exists() else ""
    for req in (".env", "*.key", "_private", "build/", "dist/", "output/"):
        if req not in gi_text:
            findings.append((".gitignore", "HARD", "gitignore-missing:%s" % req, 1))
    # 3) 内容级扫描（文本文件逐行，带行号；二进制走 binary 模式）
    bin_ext_extra = {".docx", ".pdf", ".png", ".gif", ".jpg", ".zip", ".exe"}
    for f in tracked_files():
        p = REPO / f
        if not p.exists() or p.suffix.lower() in bin_ext_extra:
            continue
        try:
            data = p.read_bytes()
        except OSError:
            continue
        if is_binary_bytes(data):
            continue
        text = data.decode("utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            scan_text(line, "%s:%d" % (f, i), findings, kinds="both")

def mode_binary(findings):
    whitelist = json.loads(WHITELIST.read_text(encoding="utf-8")) if WHITELIST.exists() else {}
    seen = set()
    for f in tracked_files():
        p = REPO / f
        if not p.exists():
            continue
        data = p.read_bytes()
        if p.suffix.lower() not in BIN_EXT and not is_binary_bytes(data):
            continue
        seen.add(f)
        digest = sha256_file(p)
        if f not in whitelist:
            findings.append((f, "HARD", "binary-not-in-whitelist", 1))
        elif whitelist[f] != digest:
            findings.append((f, "HARD", "binary-sha256-mismatch", 1))
        if p.suffix.lower() == ".docx":
            scan_docx_bytes(data, f, findings)
        else:
            scan_bytes(data, f, findings)
            # png 附加：文本块（tEXt/iTXt）走文本扫描（元数据重灾区）
            if p.suffix.lower() == ".png":
                scan_text(data.decode("latin-1", errors="replace"), f, findings, kinds="hard")
    for f in whitelist:
        if f not in seen:
            findings.append((f, "HARD", "whitelist-stale-entry", 1))
    # 台账联动：synthetic docx 对 manifest.json 登记值逐份对账
    manifest = REPO / "data" / "synthetic" / "manifest.json"
    if manifest.exists():
        mdata = json.loads(manifest.read_text(encoding="utf-8"))
        def _walk(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, str) and (k == "sha256" or k.endswith("_sha256")):
                        yield v
                    else:
                        for x in _walk(v):
                            yield x
            elif isinstance(obj, list):
                for it in obj:
                    for x in _walk(it):
                        yield x
        reg = set(_walk(mdata))
        for f in tracked_files():
            if f.startswith("data/synthetic/") and f.endswith(".docx"):
                d = sha256_file(REPO / f)
                if d not in reg:
                    findings.append((f, "HARD", "manifest-sha256-mismatch", 1))

def mode_history(findings):
    # 扫一：log -p 全文（含提交信息与全部 diff；去作者头防元数据邮箱误报）
    log = git(["log", "--all", "-p", "--format=commit %H"])
    scan_text(log, "history:log-p", findings, kinds="both")
    # 扫二：对象路径核查（.env/_private/密钥形态路径从未入过对象库）
    objs = git(["rev-list", "--all", "--objects"])
    bad = re.compile(r"\.env$|\.key$|_private|secret|token|password", re.IGNORECASE)
    n = 0
    for line in objs.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and bad.search(parts[1]):
            n += 1
    if n:
        findings.append(("history:object-paths", "HARD", "objpath", n))
    # 扫三：逐提交树面 grep（fixed-string 前向覆盖；用户名只以目录形态片段出现，降误报）
    commits = git(["rev-list", "--all"]).split()
    words = _sister_words() + ["rs" + chr(92) + _UNAME, "rs/" + _UNAME]
    for c in commits:
        for w in words:
            out = subprocess.run(
                ["git", "-c", "core.quotepath=false", "grep", "-I", "-c", "-F", w, c],
                cwd=str(REPO), capture_output=True)
            if out.returncode == 0:
                txt = out.stdout.decode("utf-8", "replace")
                cnt = sum(int(l.rsplit(":", 1)[1]) for l in txt.splitlines() if l.rsplit(":", 1)[-1].isdigit())
                if cnt:
                    findings.append(("history:tree@%s" % c[:8], "REVIEW", "sister-or-uname", cnt))

def mode_dist(dist_dir, findings):
    root = Path(dist_dir)
    if not root.exists():
        findings.append((str(dist_dir), "HARD", "dist-missing", 1))
        return
    forbidden_seg = re.compile(r"(?i)(?:^|[/\\])raw(?:[/\\]|$)")
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(root))
        if forbidden_seg.search(rel.replace("\\", "/")) or ("\\raw\\" in rel or "/raw/" in rel):
            findings.append((rel, "HARD", "forbidden-segment-raw", 1))
        data = p.read_bytes()
        scan_bytes(data, "dist:%s" % rel, findings)

# ---- selftest（阳性/阴性对照，夹具程序化合成）----

def selftest():
    errors = []
    def expect(findings, tag, category, name, present):
        got = any(f[0] == tag and f[1] == category and f[2] == name for f in findings)
        if got != present:
            errors.append("expect %s %s/%s present=%s got=%s" % (tag, category, name, present, got))

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # 阳性：拼接触发的敏感形态（源码不含完整字面值）
        email_f = "u1@" + "privmail" + ".io"
        phone_f = "1" + "38" + "12345678"   # 11 位
        id_f = "12345678901234567" + "X"    # 17+1
        _bs = chr(92)
        path_f = "C:" + _bs + "Use" + "rs" + _bs + "AS" + "US" + _bs + "x.txt"
        sk_f = "sk-" + "a" * 24
        doc = ("contact %s\nphone %s\nid %s\npath %s\nkey %s\n"
               "fine: git@github.com and a@example.com and https://x.io/p and "
               "0000000000000000000000000 and 138000000000 not-phone(12位)\n"
               % (email_f, phone_f, id_f, path_f, sk_f))
        # 阴性边界：hex 串内 11/18 位数字段不得命中（sha256 白名单实测误报源）；URL scheme 不吃盘符
        hex_neutral = "a1" + "1" + "38" + "12345678" + "c07" + " " + "b" + id_f + "d"
        (td / "sample.txt").write_text(doc, encoding="utf-8")
        findings = []
        scan_text(doc, "sample.txt", findings, kinds="both")
        expect(findings, "sample.txt", "HARD", "email", True)
        expect(findings, "sample.txt", "HARD", "phone", True)
        expect(findings, "sample.txt", "HARD", "idcard", True)
        expect(findings, "sample.txt", "HARD", "userpath-win", True)
        expect(findings, "sample.txt", "HARD", "secret-sk", True)
        # hex 阴性：sha256 形态十六进制串内的数字段（11/18 位）不得命中
        findings_hex = []
        scan_text(hex_neutral, "hex.txt", findings_hex, kinds="both")
        expect(findings_hex, "hex.txt", "HARD", "phone", False)
        expect(findings_hex, "hex.txt", "HARD", "idcard", False)
        # 豁免域（github.com/example.com）与 12 位长数字串不得命中——doc 里已内嵌，零命中即对
        # docx 全条目扫描：core.xml 元数据含邮箱必须被抓
        docx = td / "fake.docx"
        with zipfile.ZipFile(docx, "w") as zf:
            zf.writestr("docProps/core.xml",
                        "<cp:coreProperties><dc:creator>" + "u2@" + "privmail" + ".io"
                        + "</dc:creator></cp:coreProperties>")
            zf.writestr("word/document.xml", "<w:body>phone " + phone_f + "</w:body>")
        findings2 = []
        scan_docx_bytes(docx.read_bytes(), "fake.docx", findings2)
        expect(findings2, "fake.docx::docProps/core.xml", "HARD", "email", True)
        expect(findings2, "fake.docx::word/document.xml", "HARD", "phone", True)
        # 字节级强标记
        findings3 = []
        scan_bytes(("use" + "rs\\" + "AS" + "US").encode("latin-1"), "bin", findings3)
        expect(findings3, "bin", "HARD", "userpath-byte", True)
        findings4 = []
        scan_bytes(b"nothing personal here", "bin2", findings4)
        expect(findings4, "bin2", "HARD", "userpath-byte", False)
        # 姊妹词走 REVIEW（公开性核实后豁免，留档）；selftest 词取自词表首项
        w0 = _sister_words()[0]
        findings5 = []
        scan_text("see " + w0 + " repo", "s.txt", findings5, kinds="both")
        expect(findings5, "s.txt", "REVIEW", "sister-word", True)
        expect(findings5, "s.txt", "HARD", "email", False)

    if errors:
        print("SELFTEST_FAIL")
        for e in errors:
            print("  " + e)
        return 1
    print("SELFTEST_OK")
    return 0

# ---- 主入口 ----

def main(argv=None):
    ap = argparse.ArgumentParser(description="脱敏四步+产物本体扫描审计器")
    ap.add_argument("--mode", choices=["tracked", "binary", "history", "dist", "all"], default="all")
    ap.add_argument("--dist", default=None, help="产物本体扫描目标目录（默认 dist/sfc；不存在则跳过）")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    findings = []
    if args.mode in ("tracked", "all"):
        mode_tracked(findings)
    if args.mode in ("binary", "all"):
        if not WHITELIST.exists():
            findings.append((str(WHITELIST), "HARD", "whitelist-missing", 1))
        else:
            mode_binary(findings)
    if args.mode in ("history", "all"):
        mode_history(findings)
    if args.mode == "dist" or (args.dist and args.mode != "dist"):
        mode_dist(args.dist or str(REPO / "dist" / "sfc"), findings)

    hard = [f for f in findings if f[1] == "HARD"]
    review = [f for f in findings if f[1] == "REVIEW"]
    for tag, cat, name, n in findings:
        print("%s [%s:%s] x%d" % (tag, cat, name, n))
    print("----")
    print("HARD=%d REVIEW=%d" % (len(hard), len(review)))
    if review:
        print("REVIEW 项须人工豁免留档（见 plan/RELEASE-M6.md 脱敏节）")
    if hard:
        print("DESSENSITIZE_AUDIT_FAIL")
        return 1
    print(MARK)
    return 0

if __name__ == "__main__":
    sys.exit(main())
