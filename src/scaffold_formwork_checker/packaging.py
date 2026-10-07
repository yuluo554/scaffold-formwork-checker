# -*- coding: utf-8 -*-
"""M5 打包纪律（plan/05 M5 DoD ④⑤）：datas 白名单 + dist 禁区扫描 + 内嵌数据对账。

单一事实源：spec（tools/sfc.spec）与构建后断言（tools/build_exe.py）都从本
模块取白名单与扫描器，杜绝"spec 手改绕过"。

版权红线（决策 #25，HANDOFF-M5 口径 5）：规范原文全文只存 data/knowledge/raw/
（gitignored）——raw/ 及任何禁区路径段**绝不入包**；包内运行数据白名单只有：
- 包内规则表 checks.json（rules/ 目录旁路加载，决策 #25）；
- data/knowledge/clauses/*.json（条款库/公式表/阈值表/危大清单，全部要点制）；
- data/examples/*.json（算例真值库，bench examples 套件）；
- data/synthetic/*（冻结 fixtures，bench synthetic 套件）。
"""

import hashlib
import os

# 禁区路径段：dist 树内任一文件/目录命中即失败（构建后断言 + 测试双守门）
FORBIDDEN_SEGMENTS = ("raw",)

# 内嵌数据白名单：（data 子目录, 收集的扩展名）；数据一律落 dist 内 data/<子目录>
DATA_SOURCES = [
    ("knowledge/clauses", (".json",)),
    ("examples", (".json",)),
    ("synthetic", (".docx", ".json")),
]

# 惰性导入的外部依赖显式覆盖（PyInstaller 静态分析对运行期 __import__ 不可见；
# parse 报告组依赖 docx/pypdf——漏一个即冻结 exe 缺核心能力而源码态测试全绿）
HIDDENIMPORTS = ["docx", "pypdf"]

APP_NAME = "sfc"
CHECKS_REL = os.path.join("scaffold_formwork_checker", "rules", "checks.json")


class PackagingViolation(Exception):
    """打包纪律违反（禁区成分/白名单外数据）。"""


def _has_forbidden(path):
    parts = path.replace("\\", "/").lower().split("/")
    return any(part in FORBIDDEN_SEGMENTS for part in parts)


def _assert_clean(datas):
    for src, dest in datas:
        if _has_forbidden(src) or _has_forbidden(dest):
            raise PackagingViolation(
                "datas 白名单含禁区路径段 %r（红线：raw/ 绝不入包）" % ((src, dest),))


def build_datas(root):
    """构建 spec datas 白名单：[(绝对路径, dist 内目标目录), ...]。

    禁区断言内置：任何来源路径含禁区段（如 data/knowledge/raw/）即抛
    PackagingViolation——spec 只能拿白名单，拿不到别的。
    """
    datas = []
    checks = os.path.join(root, "src", CHECKS_REL.replace("\\", "/"))
    if not os.path.isfile(checks):
        raise PackagingViolation("包内规则表缺失：%s" % checks)
    datas.append((checks, os.path.dirname(CHECKS_REL.replace("\\", "/"))))
    for sub, exts in DATA_SOURCES:
        directory = os.path.join(root, "data", *sub.split("/"))
        if not os.path.isdir(directory):
            raise PackagingViolation("白名单数据目录缺失：%s" % directory)
        for name in sorted(os.listdir(directory)):
            if os.path.splitext(name)[1].lower() in exts:
                datas.append((os.path.join(directory, name),
                              os.path.join("data", *sub.split("/"))))
    _assert_clean(datas)
    return datas


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_dist(dist_dir, root, app_name=APP_NAME):
    """构建后断言（DoD ④）：禁区扫描 + 内嵌数据对账。返回错误串列表（空=过）。

    1. dist 树任何路径段命中禁区（raw/ 等）→ 违规；
    2. 白名单 datas 逐份在内嵌数据根存在且 sha256 与仓库一致（缺失/漂移即违规）；
    3. 白名单声明目录（data/ 全树 + 包 rules 目录）内无白名单外多余文件。
    """
    errors = []
    app_dir = os.path.join(dist_dir, app_name)
    if not os.path.isdir(app_dir):
        return ["dist 应用目录不存在：%s" % app_dir]

    # 1) 禁区成分全树扫描
    for dirpath, dirnames, filenames in os.walk(app_dir):
        for name in list(dirnames) + filenames:
            if name.lower() in FORBIDDEN_SEGMENTS:
                errors.append("禁区成分：%s"
                              % os.path.join(os.path.relpath(dirpath, app_dir), name))

    datas = build_datas(root)
    bases = [b for b in (app_dir, os.path.join(app_dir, "_internal"))
             if os.path.isdir(b)]
    if not bases:
        return errors + ["内嵌数据根不存在（exe 目录 / _internal 均无）"]

    # 2) 逐份对账（PyInstaller 5.x 数据平铺 exe 目录，6.x 在 _internal）
    expected = {}
    for src, dest in datas:
        rel = dest.replace("\\", "/") + "/" + os.path.basename(src)
        expected[rel] = src
    for rel in sorted(expected):
        hits = [os.path.join(b, rel.replace("/", os.sep)) for b in bases
                if os.path.isfile(os.path.join(b, rel.replace("/", os.sep)))]
        if not hits:
            errors.append("内嵌数据缺失：%s" % rel)
        elif _sha256(hits[0]) != _sha256(expected[rel]):
            errors.append("内嵌数据不一致：%s" % rel)

    # 3) 白名单声明目录内无多余文件
    for b in bases:
        tops = [os.path.join(b, "data"),
                os.path.join(b, "scaffold_formwork_checker", "rules")]
        for top in tops:
            if not os.path.isdir(top):
                continue
            for dirpath, _dirnames, filenames in os.walk(top):
                for name in filenames:
                    rel = os.path.relpath(os.path.join(dirpath, name), b)
                    rel = rel.replace("\\", "/")
                    if rel not in expected:
                        errors.append("内嵌数据多余（白名单外）：%s" % rel)
    return errors
