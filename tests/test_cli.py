"""CLI 行为守门：退出码语义锁定（plan/03 §2 D5 口径，后续重构不得漂移）。"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from scaffold_formwork_checker import __version__
from scaffold_formwork_checker.cli import (
    EXIT_DEGRADED,
    EXIT_INPUT_ERROR,
    EXIT_OK,
    main,
)


def test_exit_code_semantics_are_locked():
    assert EXIT_OK == 0
    assert EXIT_DEGRADED == 1
    assert EXIT_INPUT_ERROR == 2


def test_selfcheck_exits_ok(capsys):
    assert main(["selfcheck"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "sfc" in out
    assert __version__ in out


def test_no_command_is_input_error(capsys):
    assert main([]) == EXIT_INPUT_ERROR
    assert "usage" in capsys.readouterr().out.lower()


def test_unknown_command_system_exit_2():
    with pytest.raises(SystemExit) as exc:
        main(["bogus-command"])
    assert exc.value.code == 2


def test_version_flag_exits_zero():
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0


def test_console_script_entrypoint():
    """pip 安装态下验证 sfc 可执行文件真实可用（打包元数据冒烟）。"""
    exe_dir = Path(sys.executable).parent
    exe = exe_dir / ("sfc.exe" if os.name == "nt" else "sfc")
    if not exe.exists():
        pytest.skip("console script 未安装（非 pip 安装环境）")
    proc = subprocess.run(
        [str(exe), "--version"], capture_output=True, text=True, timeout=120
    )
    assert proc.returncode == 0
    assert __version__ in proc.stdout
