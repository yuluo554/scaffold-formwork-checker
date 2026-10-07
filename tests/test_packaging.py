# -*- coding: utf-8 -*-
"""M5 打包纪律守门测试（plan/05 M5 DoD ⑤，skill 实录：spec 双守门）。

- datas 单一事实源：spec 只允许从 packaging.build_datas 拿白名单
  （文本断言 spec 未手写数据路径）；
- 白名单内容与仓库数据目录对账、禁区段（raw/）零出现；
- hiddenimports 覆盖惰性导入的外部依赖（漏一个 = 冻结 exe 缺能力而
  源码态测试全绿的静默坑）；
- scan_dist 三断言（禁区/缺失漂移/白名单外多余）正反用例。
"""
import os
import shutil
from pathlib import Path

import pytest

from scaffold_formwork_checker import packaging
from scaffold_formwork_checker.packaging import (
    DATA_SOURCES, FORBIDDEN_SEGMENTS, HIDDENIMPORTS, PackagingViolation,
    build_datas, scan_dist,
)

_REPO = Path(__file__).resolve().parent.parent
_SPEC = (_REPO / "tools" / "sfc.spec").read_text(encoding="utf-8")


# ---- spec 白名单守门（防手改绕过）----

def test_spec_datas_comes_from_build_datas():
    assert "build_datas(ROOT)" in _SPEC
    assert "HIDDENIMPORTS" in _SPEC


def test_spec_has_no_handwritten_data_paths():
    """spec 文本不允许出现任何手写数据路径与禁区字面（只准白名单函数）。"""
    for banned in ("data/", "knowledge", "examples", "synthetic", "raw"):
        assert banned not in _SPEC, banned


def test_spec_gitignore_exception_in_place():
    gitignore = (_REPO / ".gitignore").read_text(encoding="utf-8")
    assert "*.spec" in gitignore
    assert "!tools/*.spec" in gitignore


def test_entry_scripts_exist():
    for name in ("_entry_sfc.py", "_entry_gui.py", "build_exe.py"):
        assert (_REPO / "tools" / name).is_file()
    entry_gui = (_REPO / "tools" / "_entry_gui.py").read_text(encoding="utf-8")
    assert "gui.app import main" in entry_gui
    entry_sfc = (_REPO / "tools" / "_entry_sfc.py").read_text(encoding="utf-8")
    assert "cli import main" in entry_sfc


# ---- hiddenimports 覆盖惰性导入 ----

def test_hiddenimports_cover_lazy_external_deps():
    assert {"docx", "pypdf"} <= set(HIDDENIMPORTS)


# ---- 白名单内容 ----

def test_build_datas_matches_repo_layout():
    datas = build_datas(str(_REPO))
    rels = set()
    for src, dest in datas:
        path = Path(src)
        rel = (dest.replace("\\", "/") + "/" + path.name)
        rels.add(rel)
        assert Path(src).is_file()
    # 包内规则表
    assert "scaffold_formwork_checker/rules/checks.json" in rels
    # data 白名单三目录与文件系统逐份一致
    for sub, exts in DATA_SOURCES:
        directory = _REPO / "data" / sub
        expected = {("data/%s/%s" % (sub, p.name))
                    for p in directory.iterdir()
                    if p.suffix.lower() in exts}
        got = {r for r in rels if r.startswith("data/%s/" % sub)}
        assert got == expected, sub


def test_build_datas_no_forbidden_segments():
    datas = build_datas(str(_REPO))
    for src, dest in datas:
        for part in src.replace("\\", "/").split("/") + dest.replace("\\", "/").split("/"):
            assert part.lower() not in FORBIDDEN_SEGMENTS


def test_build_datas_excludes_raw_in_fake_root(tmp_path):
    """raw/ 即使存在也不入包（版权红线）；其余白名单目录正常收集。"""
    clauses = tmp_path / "data" / "knowledge" / "clauses"
    raw = tmp_path / "data" / "knowledge" / "raw"
    examples = tmp_path / "data" / "examples"
    synthetic = tmp_path / "data" / "synthetic"
    for d in (clauses, raw, examples, synthetic):
        d.mkdir(parents=True)
    rules = tmp_path / "src" / "scaffold_formwork_checker" / "rules"
    rules.mkdir(parents=True)
    (rules / "checks.json").write_text("{}", encoding="utf-8")
    (clauses / "formulas.json").write_text("{}", encoding="utf-8")
    (raw / "jgj130-full.json").write_text("{}", encoding="utf-8")
    (examples / "EX-x.json").write_text("{}", encoding="utf-8")
    datas = build_datas(str(tmp_path))
    rels = {os.path.join(dest, os.path.basename(src)).replace("\\", "/")
            for src, dest in datas}
    assert "data/knowledge/clauses/formulas.json" in rels
    assert "data/examples/EX-x.json" in rels
    assert not any("raw" in r.split("/") for r in rels)


def test_build_datas_rejects_forbidden_source(tmp_path, monkeypatch):
    """白名单数据源被改成禁区目录 → PackagingViolation（守门生效）。"""
    bad_raw = tmp_path / "data" / "knowledge" / "raw"
    bad_raw.mkdir(parents=True)
    (bad_raw / "full.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(packaging, "DATA_SOURCES",
                        [("knowledge/raw", (".json",))])
    with pytest.raises(PackagingViolation):
        build_datas(str(tmp_path))


def test_build_datas_missing_dirs_raise(tmp_path):
    with pytest.raises(PackagingViolation):
        build_datas(str(tmp_path))


# ---- scan_dist 三断言 ----

@pytest.fixture()
def fake_dist(tmp_path):
    """迷你仓库根 + 已构建 dist（6.x 布局 _internal）。"""
    root = tmp_path / "repo"
    clauses = root / "data" / "knowledge" / "clauses"
    examples = root / "data" / "examples"
    synthetic = root / "data" / "synthetic"
    rules = root / "src" / "scaffold_formwork_checker" / "rules"
    for d in (clauses, examples, synthetic, rules):
        d.mkdir(parents=True)
    (rules / "checks.json").write_text("{}", encoding="utf-8")
    (clauses / "formulas.json").write_text("A", encoding="utf-8")
    (examples / "EX-x.json").write_text("B", encoding="utf-8")
    (synthetic / "SY-x.docx").write_bytes(b"docx")
    (synthetic / "manifest.json").write_text("C", encoding="utf-8")

    dist = tmp_path / "dist"
    app = dist / "sfc"
    internal = app / "_internal"
    for rel in ("data/knowledge/clauses", "data/examples", "data/synthetic",
                "scaffold_formwork_checker/rules"):
        (internal / rel).mkdir(parents=True)
    (app / "sfc.exe").write_bytes(b"mz")
    (app / "sfc-gui.exe").write_bytes(b"mz")
    (internal / "data/knowledge/clauses/formulas.json").write_text("A", encoding="utf-8")
    (internal / "data/examples/EX-x.json").write_text("B", encoding="utf-8")
    (internal / "data/synthetic/SY-x.docx").write_bytes(b"docx")
    (internal / "data/synthetic/manifest.json").write_text("C", encoding="utf-8")
    (internal / "scaffold_formwork_checker/rules/checks.json").write_text("{}", encoding="utf-8")
    return root, dist


def test_scan_dist_clean_passes(fake_dist):
    root, dist = fake_dist
    assert scan_dist(str(dist), str(root)) == []


def test_scan_dist_detects_forbidden(fake_dist):
    root, dist = fake_dist
    bad = dist / "sfc" / "_internal" / "data" / "knowledge" / "raw"
    bad.mkdir()
    (bad / "full.json").write_text("{}", encoding="utf-8")
    errors = scan_dist(str(dist), str(root))
    assert any("禁区成分" in e for e in errors)


def test_scan_dist_detects_drift(fake_dist):
    root, dist = fake_dist
    target = dist / "sfc" / "_internal" / "data" / "examples" / "EX-x.json"
    target.write_text("DRIFTED", encoding="utf-8")
    errors = scan_dist(str(dist), str(root))
    assert any("内嵌数据不一致" in e for e in errors)


def test_scan_dist_detects_missing(fake_dist):
    root, dist = fake_dist
    (dist / "sfc" / "_internal" / "data" / "synthetic" / "SY-x.docx").unlink()
    errors = scan_dist(str(dist), str(root))
    assert any("内嵌数据缺失" in e for e in errors)


def test_scan_dist_detects_extra_files(fake_dist):
    root, dist = fake_dist
    smuggled = dist / "sfc" / "_internal" / "data" / "examples" / "SMUGGLED.json"
    smuggled.write_text("{}", encoding="utf-8")
    errors = scan_dist(str(dist), str(root))
    assert any("白名单外" in e for e in errors)


def test_scan_dist_pyinstaller5_layout_passes(tmp_path):
    """5.x 平铺布局（数据在 exe 目录旁）同样通过对账。"""
    root = tmp_path / "repo"
    rules = root / "src" / "scaffold_formwork_checker" / "rules"
    clauses = root / "data" / "knowledge" / "clauses"
    examples = root / "data" / "examples"
    synthetic = root / "data" / "synthetic"
    for d in (rules, clauses, examples, synthetic):
        d.mkdir(parents=True)
    (rules / "checks.json").write_text("{}", encoding="utf-8")
    (clauses / "formulas.json").write_text("A", encoding="utf-8")
    (examples / "EX-x.json").write_text("B", encoding="utf-8")
    (synthetic / "manifest.json").write_text("C", encoding="utf-8")
    dist = tmp_path / "dist"
    app = dist / "sfc"
    for rel in ("data/knowledge/clauses", "data/examples", "data/synthetic",
                "scaffold_formwork_checker/rules"):
        (app / rel).mkdir(parents=True)
    (app / "sfc.exe").write_bytes(b"mz")
    (app / "data/knowledge/clauses/formulas.json").write_text("A", encoding="utf-8")
    (app / "data/examples/EX-x.json").write_text("B", encoding="utf-8")
    (app / "data/synthetic/manifest.json").write_text("C", encoding="utf-8")
    (app / "scaffold_formwork_checker/rules/checks.json").write_text("{}", encoding="utf-8")
    assert scan_dist(str(dist), str(root)) == []
    shutil.rmtree(tmp_path / "dist", ignore_errors=True)
