# -*- coding: utf-8 -*-
"""EOL/冻结纪律守门（M1 DoD ④：EOL/冻结纪律测试全绿）。

- CR 门：仓库文本文件出现 CR 即大声失败（.gitattributes eol=lf 的运行时对账；
  Windows 开发机 autocrlf 漏网、后续误存 CRLF 都会在此拦截）；
- 扫描范围=仓库树内全部 *.py/*.json/*.md/*.toml/*.yml/*.txt/*.cfg/.gitattributes，
  排除 data/knowledge/raw/（原文存档，gitignored，允许任意字节）与二进制
  （docx/jpg/png 为 zip/图像容器，不适用文本 CR 门）。
"""

import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEXT_SUFFIXES = (
    ".py", ".json", ".md", ".toml", ".yml", ".yaml", ".txt", ".cfg", ".in",
)
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache",
             "node_modules", "build", "dist", ".idea", ".vscode",
             "output", "reports"}  # gitignored 运行草稿/产物目录不入 CR 门
# raw/ 是版权红线本地存档（gitignored），字节不受 EOL 门约束
SKIP_PARTS = (os.path.join("data", "knowledge", "raw"),)


def _iter_text_files():
    for base, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        rel_base = os.path.relpath(base, REPO_ROOT)
        if any(rel_base.startswith(p) or rel_base == p for p in SKIP_PARTS):
            continue
        for name in files:
            if name in (".gitattributes", ".gitignore") or name.endswith(TEXT_SUFFIXES):
                yield os.path.join(base, name)


def test_no_carriage_return_in_tracked_text_files():
    offenders = []
    for path in _iter_text_files():
        with open(path, "rb") as f:
            data = f.read()
        if b"\r" in data:
            offenders.append(os.path.relpath(path, REPO_ROOT))
    assert not offenders, "文本文件含 CR（应为 LF，见 .gitattributes eol=lf）:\n" + "\n".join(offenders)


def test_frozen_data_dirs_are_gitkeep_free_but_populated():
    """M1 后 data/ 三个数据目录都应有真实内容（骨架 .gitkeep 应被移除）。"""
    for d, min_files in (
        (os.path.join("data", "examples"), 10),
        (os.path.join("data", "synthetic"), 12),
        (os.path.join("data", "knowledge", "clauses"), 6),
    ):
        full = os.path.join(REPO_ROOT, d)
        names = [n for n in os.listdir(full) if not n.startswith(".")]
        assert len(names) >= min_files, (d, names)
        assert ".gitkeep" not in names, d
