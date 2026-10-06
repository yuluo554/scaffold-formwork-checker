"""sfc —— 命令行入口。

退出码语义（口径锁定，plan/03 §2 D5；tests/test_cli.py 守门）：
  0 = 完成
  1 = 降级完成（结果可用，但含"待人工确认"项）
  2 = 输入不可用 / 参数错误

子命令随里程碑扩展：calc（M2 验算）、check/grade（M3 核查与分级）、
report（M4 导出）、bench（M4 基准）。本文件只保留骨架可用的最小集。
"""

import argparse
import os
import sys

from . import __version__

EXIT_OK = 0
EXIT_DEGRADED = 1
EXIT_INPUT_ERROR = 2

_DESCRIPTION = (
    "脚手架与模板支架安全验算及危大分级工具"
    "（JGJ 130-2011 / JGJ 162-2008 / 住建部令第37号 / 建办质〔2018〕31号）"
)


def _force_utf8_stdio() -> None:
    """Windows 控制台/管道默认本地码页会击穿中文输出，统一改 UTF-8（失败不致命）。"""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sfc", description=_DESCRIPTION)
    parser.add_argument("--version", action="version", version="sfc " + __version__)
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.add_parser(
        "selfcheck", help="运行环境自检：版本 / 解释器 / 可选依赖组 / 数据目录"
    )
    return parser


def _optional_deps_status() -> "list[str]":
    """报告 extras 依赖可用性（仅信息性；未安装属正常，不代表降级）。"""
    groups = [
        ("parse", ("docx", "pypdf")),
        ("report", ("docx",)),
        ("gui", ("PySide6",)),
    ]
    lines = []
    for group, modules in groups:
        states = []
        for name in modules:
            try:
                __import__(name)
            except ImportError:
                states.append(name + ":未安装")
            else:
                states.append(name + ":可用")
        lines.append("  extras %-6s: %s" % (group, ", ".join(states)))
    return lines


def _find_data_dir() -> "str | None":
    """从 CWD 上溯找 data/（信息性探测；打包内嵌查找分支按 plan/03 D8 于 M5 冻结实现）。"""
    base = os.getcwd()
    for _ in range(4):
        candidate = os.path.join(base, "data")
        if os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(base)
        if parent == base:
            break
        base = parent
    return None


def _run_selfcheck() -> int:
    print("sfc selfcheck")
    print("  版本    : " + __version__)
    print(
        "  解释器  : Python %s (%s)"
        % (sys.version.split()[0], sys.platform)
    )
    for line in _optional_deps_status():
        print(line)
    data_dir = _find_data_dir()
    print("  数据目录: %s" % (data_dir if data_dir else "未找到（信息性，M1 起使用）"))
    return EXIT_OK


def main(argv=None) -> int:
    _force_utf8_stdio()
    parser = build_parser()
    # 未知子命令 / 坏参数：argparse 自行 SystemExit(2)，与本文件退出码口径一致
    args = parser.parse_args(argv)
    if args.command == "selfcheck":
        return _run_selfcheck()
    parser.print_help()
    return EXIT_INPUT_ERROR


if __name__ == "__main__":
    sys.exit(main())
