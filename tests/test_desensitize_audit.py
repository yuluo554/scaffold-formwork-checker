# -*- coding: utf-8 -*-
"""脱敏审计器守门测试（M6 发布门常驻闸门）。

被测物：tools/desensitize_audit.py（脱敏四步+产物本体扫描，子进程实跑）。
- selftest 阳性/阴性对照必须自证有效（夹具程序化合成，无字面敏感值）；
- tracked/binary/history 三模式对当前仓库必须全绿（HARD=0）；
- dist 产物扫描在无构建产物环境（CI/干净 clone）声明式跳过；
- 全过标记词 DESSENSITIZE_AUDIT_OK 必须出现（防"静默少扫"）。
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
AUDIT = REPO / "tools" / "desensitize_audit.py"


def _run(*args):
    out = subprocess.run(
        [sys.executable, "-X", "utf8", str(AUDIT)] + list(args),
        cwd=str(REPO), capture_output=True)
    text = out.stdout.decode("utf-8", "replace") + out.stderr.decode("utf-8", "replace")
    return out.returncode, text


def test_selftest_positive_controls():
    code, out = _run("--selftest")
    assert code == 0, out
    assert "SELFTEST_OK" in out


def test_tracked_scan_clean():
    code, out = _run("--mode", "tracked")
    assert code == 0, out


def test_binary_scan_clean():
    code, out = _run("--mode", "binary")
    assert code == 0, out


def test_history_scan_clean():
    code, out = _run("--mode", "history")
    assert code == 0, out


def test_full_audit_prints_mark():
    code, out = _run()
    assert code == 0, out
    assert "DESSENSITIZE_AUDIT_OK" in out


def test_dist_scan_clean_or_absent():
    if not (REPO / "dist" / "sfc").exists():
        # 声明式跳过：CI/干净 clone 无构建产物（对账见 plan/RELEASE-M6.md）
        import pytest
        pytest.skip("dist/sfc 不存在（未构建产物）")
    code, out = _run("--mode", "dist")
    assert code == 0, out
