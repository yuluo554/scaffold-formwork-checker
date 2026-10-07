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


def test_gui_subcommand_lazy_import_static():
    """sfc gui 为惰性导入：cli 模块级（函数体之外）不得引用 gui/PySide6。

    用 AST 静态守门而非 sys.modules 断言——pytest 收集阶段即导入全部测试
    模块，装了 PySide6 的开发环境里 sys.modules 断言必假失败。
    """
    import ast

    import scaffold_formwork_checker.cli as cli_module
    from scaffold_formwork_checker.cli import build_parser

    args = build_parser().parse_args(["gui"])
    assert args.command == "gui"
    assert args.data_dir is None

    tree = ast.parse(
        Path(cli_module.__file__).read_text(encoding="utf-8"))
    stack = list(tree.body)
    while stack:
        node = stack.pop(0)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue  # 函数体内 = 惰性，允许
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
            assert not any(n.startswith("PySide6") or n.endswith(".gui")
                           for n in names), names
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            assert not mod.startswith("PySide6")
            assert mod not in ("gui",) and not mod.endswith(".gui"), mod
        stack.extend(ast.iter_child_nodes(node))


def test_gui_import_error_prints_hint_and_exits_2(capsys, monkeypatch):
    """PySide6 缺失：打印安装提示，exit 2（输入不可用口径），不崩溃。"""
    monkeypatch.setitem(sys.modules, "scaffold_formwork_checker.gui.app", None)
    assert main(["gui"]) == EXIT_INPUT_ERROR
    err = capsys.readouterr().err
    assert "GUI 依赖未安装" in err
    assert ".[gui]" in err
