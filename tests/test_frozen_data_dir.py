# -*- coding: utf-8 -*-
"""M5 数据内嵌查找分支锁死测试（plan/05 M5 DoD ③）。

冻结优先级口径（HANDOFF-M5 既定口径，改动即口径变更）：
  显式参数 > SFC_DATA 环境变量 > sys._MEIPASS/data（PyInstaller 运行期解包根）
  > <exe目录>/_internal/data（PyInstaller 6 布局兜底）> <exe目录>/data（5.x 布局兜底）
  > CWD 上溯 > 包相对上溯。

冻结分支必须整体排在 CWD 上溯之前：exe 内嵌数据优先于工作目录发现，
防"仓库树内跑 exe 命中仓库 data，内嵌数据验了个寂寞"（假结果陷阱）。
"""
import os
import sys

import pytest

from scaffold_formwork_checker.engine.loader import find_data_dir


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("SFC_DATA", raising=False)


def _make_data(root):
    clauses = os.path.join(root, "data", "knowledge", "clauses")
    os.makedirs(clauses)
    with open(os.path.join(clauses, "formulas.json"), "w", encoding="utf-8") as f:
        f.write('{"formulas": []}')


def _set_frozen(monkeypatch, exe_path, meipass=None):
    if meipass is not None:
        monkeypatch.setattr(sys, "_MEIPASS", meipass, raising=False)
    else:
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", exe_path, raising=False)


def _clear_frozen(monkeypatch):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)


def test_not_frozen_no_candidates(monkeypatch):
    _clear_frozen(monkeypatch)
    from scaffold_formwork_checker.engine.loader import _frozen_data_candidates
    assert _frozen_data_candidates() == []


def test_candidate_order_meipass_internal_exe(monkeypatch, tmp_path):
    exe = tmp_path / "app" / "sfc.exe"
    exe.parent.mkdir()
    _set_frozen(monkeypatch, str(exe), meipass=str(tmp_path / "app" / "_internal"))
    from scaffold_formwork_checker.engine.loader import _frozen_data_candidates
    cands = _frozen_data_candidates()
    assert cands == [
        str(tmp_path / "app" / "_internal" / "data"),
        str(tmp_path / "app" / "_internal" / "data"),
        str(tmp_path / "app" / "data"),
    ]


def test_meipass_branch_wins_over_cwd(monkeypatch, tmp_path):
    """PyInstaller 6 布局：_MEIPASS/data 优先，且压过 CWD 上的 data。"""
    frozen_root = tmp_path / "frozen"
    (frozen_root / "_internal").mkdir(parents=True)
    _make_data(str(frozen_root / "_internal"))
    repo_like = tmp_path / "somewhere"
    _make_data(str(repo_like))
    monkeypatch.chdir(str(repo_like))
    _set_frozen(monkeypatch, str(frozen_root / "sfc.exe"),
                meipass=str(frozen_root / "_internal"))
    assert find_data_dir() == str(frozen_root / "_internal" / "data")


def test_internal_dir_branch_without_meipass(monkeypatch, tmp_path):
    """PyInstaller 6 布局 _MEIPASS 缺失兜底：<exe目录>/_internal/data。"""
    frozen_root = tmp_path / "frozen"
    (frozen_root / "_internal").mkdir(parents=True)
    _make_data(str(frozen_root / "_internal"))
    _set_frozen(monkeypatch, str(frozen_root / "sfc.exe"), meipass=None)
    assert find_data_dir() == str(frozen_root / "_internal" / "data")


def test_exe_dir_branch_pyinstaller5_layout(monkeypatch, tmp_path):
    """PyInstaller 5 布局：数据平铺 exe 目录，_MEIPASS 缺失时走 <exe目录>/data。"""
    frozen_root = tmp_path / "frozen"
    frozen_root.mkdir()
    _make_data(str(frozen_root))
    _set_frozen(monkeypatch, str(frozen_root / "sfc.exe"), meipass=None)
    assert find_data_dir() == str(frozen_root / "data")


def test_frozen_branch_ignores_cwd_data(monkeypatch, tmp_path):
    """冻结候选均未命中时才允许 CWD 回退；命中任一冻结候选即不落 CWD。"""
    frozen_root = tmp_path / "frozen"
    frozen_root.mkdir()  # 冻结侧无 data
    cwd_root = tmp_path / "cwd"
    _make_data(str(cwd_root))
    monkeypatch.chdir(str(cwd_root))
    _set_frozen(monkeypatch, str(frozen_root / "sfc.exe"), meipass=None)
    assert find_data_dir() == str(cwd_root / "data")


def test_frozen_invalid_candidates_fall_through_to_cwd(monkeypatch, tmp_path):
    """冻结候选目录存在但缺 knowledge/clauses 时继续回退（不误报不可用）。"""
    frozen_root = tmp_path / "frozen"
    (frozen_root / "_internal" / "data").mkdir(parents=True)  # 有 data 无条款库
    cwd_root = tmp_path / "cwd"
    _make_data(str(cwd_root))
    monkeypatch.chdir(str(cwd_root))
    _set_frozen(monkeypatch, str(frozen_root / "sfc.exe"),
                meipass=str(frozen_root / "_internal"))
    assert find_data_dir() == str(cwd_root / "data")


def test_explicit_still_beats_frozen(monkeypatch, tmp_path):
    frozen_root = tmp_path / "frozen"
    (frozen_root / "_internal").mkdir(parents=True)
    _make_data(str(frozen_root / "_internal"))
    explicit_root = tmp_path / "explicit"
    _make_data(str(explicit_root))
    _set_frozen(monkeypatch, str(frozen_root / "sfc.exe"),
                meipass=str(frozen_root / "_internal"))
    # 显式/env 参数语义 = data 目录本身（直接含 knowledge/clauses）
    assert find_data_dir(str(explicit_root / "data")) == str(explicit_root / "data")


def test_env_beats_frozen(monkeypatch, tmp_path):
    frozen_root = tmp_path / "frozen"
    (frozen_root / "_internal").mkdir(parents=True)
    _make_data(str(frozen_root / "_internal"))
    env_root = tmp_path / "envdata"
    _make_data(str(env_root))
    monkeypatch.setenv("SFC_DATA", str(env_root / "data"))
    _set_frozen(monkeypatch, str(frozen_root / "sfc.exe"),
                meipass=str(frozen_root / "_internal"))
    assert find_data_dir() == str(env_root / "data")


def test_dev_tree_unaffected(monkeypatch, tmp_path):
    """非冻结（开发树）环境行为不变：CWD 上溯命中即返回。"""
    _clear_frozen(monkeypatch)
    cwd_root = tmp_path / "dev"
    _make_data(str(cwd_root))
    monkeypatch.chdir(str(cwd_root))
    assert find_data_dir() == str(cwd_root / "data")
