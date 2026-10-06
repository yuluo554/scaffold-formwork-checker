"""包元数据守门。"""

from pathlib import Path

import pytest

import scaffold_formwork_checker

_ROOT = Path(__file__).resolve().parents[1]


def test_version_is_semver():
    parts = scaffold_formwork_checker.__version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts), "版本号必须是三段数字 SemVer"


def test_version_matches_pyproject():
    pyproject = _ROOT / "pyproject.toml"
    if not pyproject.exists():
        pytest.skip("pyproject.toml 不在运行目录（site-packages 安装态）")
    declared = None
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        if line.startswith("version ="):
            declared = line.split("=", 1)[1].strip().strip('"')
            break
    assert declared, "pyproject.toml 缺少 version 字段"
    assert scaffold_formwork_checker.__version__ == declared
