"""sfc —— 命令行入口。

退出码语义（口径锁定，plan/03 §2 D5；tests/test_cli.py 守门）：
  0 = 完成
  1 = 降级完成（结果可用，但含"待人工确认"项）
  2 = 输入不可用 / 参数错误

子命令随里程碑扩展：calc（M2 验算）、check/grade（M3 核查与分级）、
report（M4 导出）、bench（M4 基准）。
"""
import argparse
import json
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
    p_calc = sub.add_parser(
        "calc", help="验算：参数卡 JSON → 验算结果（应力比/结论/条款号）"
    )
    p_calc.add_argument("card", help="参数卡 JSON 文件路径")
    p_calc.add_argument(
        "--module", default=None,
        help="验算模块 M-1~M-6（缺省按参数卡内容自动识别）",
    )
    p_calc.add_argument("--data-dir", default=None, help="数据目录（含 knowledge/clauses）")
    p_calc.add_argument("--indent", type=int, default=2, help="输出 JSON 缩进（0=单行）")
    p_check = sub.add_parser(
        "check", help="核查：专项方案 docx/pdf → 违规清单 + 分级结论 + 待人工确认项"
    )
    p_check.add_argument("file", help="专项施工方案文件（.docx/.pdf）")
    p_check.add_argument("--data-dir", default=None, help="数据目录（含 knowledge/clauses）")
    p_check.add_argument("--indent", type=int, default=2, help="输出 JSON 缩进（0=单行）")
    p_grade = sub.add_parser(
        "grade", help="分级：专项方案 docx/pdf → 危大/超规模判定（结论+义务+依据摘录）"
    )
    p_grade.add_argument("file", help="专项施工方案文件（.docx/.pdf）")
    p_grade.add_argument(
        "--param", action="append", default=[], metavar="NAME=VALUE",
        help="判定参数覆盖（可多次，如 --param build_height=56；布尔用 true/false）",
    )
    p_grade.add_argument("--data-dir", default=None, help="数据目录（含 knowledge/clauses）")
    p_grade.add_argument("--indent", type=int, default=2, help="输出 JSON 缩进（0=单行）")
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


def _run_calc(args) -> int:
    """sfc calc：参数卡 JSON → 验算结果。

    退出码：0=完成；1=降级完成（模块因依据未核对被拦截，结果含说明）；
    2=输入不可用/参数错误（文件缺失、JSON 坏、参数非法、条款库不可用、模块不识别）。
    """
    from .engine import CardError, KnowledgeError, detect_module, load_knowledge, run_calc

    card_path = args.card
    if not os.path.isfile(card_path):
        print("参数卡文件不存在：%s" % card_path, file=sys.stderr)
        return EXIT_INPUT_ERROR
    try:
        with open(card_path, encoding="utf-8") as f:
            card_data = json.load(f)
    except ValueError as exc:
        print("参数卡 JSON 解析失败：%s" % exc, file=sys.stderr)
        return EXIT_INPUT_ERROR
    try:
        knowledge = load_knowledge(args.data_dir)
    except KnowledgeError as exc:
        print("条款库不可用：%s" % exc, file=sys.stderr)
        return EXIT_INPUT_ERROR
    try:
        module_id = args.module or detect_module(card_data if isinstance(card_data, dict) else {})
        result = run_calc(module_id, card_data, knowledge)
    except (CardError, KnowledgeError) as exc:
        print("参数错误：%s" % exc, file=sys.stderr)
        return EXIT_INPUT_ERROR
    indent = None if args.indent == 0 else args.indent
    print(json.dumps(result, ensure_ascii=False, indent=indent))
    if result.get("status") == "blocked":
        print("注意：%s" % result.get("status_note", ""), file=sys.stderr)
        return EXIT_DEGRADED
    return EXIT_OK


def _parse_param_override(raw):
    """--param NAME=VALUE：数值→float，true/false→bool，其余保持字符串。"""
    name, sep, value = raw.partition("=")
    if not sep or not name.strip():
        raise ValueError("--param 须为 NAME=VALUE 形式，得到 %r" % (raw,))
    v = value.strip()
    if v.lower() == "true":
        return name.strip(), True
    if v.lower() == "false":
        return name.strip(), False
    try:
        return name.strip(), float(v)
    except ValueError:
        return name.strip(), v


def _run_check(args) -> int:
    """sfc check：方案文档 → 违规清单 + 分级结论 + 待人工确认项。

    退出码：0=核查完成且无违规/待确认项；1=降级完成（存在违规项或待人工
    确认项，结果仍可用）；2=输入不可用（文件缺失/坏、解析失败、条款库或
    规则表不可用）。
    """
    from .parse import ParseError, parse_scheme
    from .rules import ChecksError, load_checks_table, run_checks
    from .engine.loader import KnowledgeError, load_knowledge

    if not os.path.isfile(args.file):
        print("方案文件不存在：%s" % args.file, file=sys.stderr)
        return EXIT_INPUT_ERROR
    try:
        parsed = parse_scheme(args.file)
    except ParseError as exc:
        print("方案解析失败：%s" % exc, file=sys.stderr)
        return EXIT_INPUT_ERROR
    try:
        knowledge = load_knowledge(args.data_dir)
        checks_table = load_checks_table()
    except (KnowledgeError, ChecksError) as exc:
        print("条款库/规则表不可用：%s" % exc, file=sys.stderr)
        return EXIT_INPUT_ERROR
    report = run_checks(parsed.scheme_card, parsed.calcbook_card, knowledge,
                        checks_table)
    report = dict(report)
    report["tool"] = "sfc check"
    report["file"] = args.file
    report["warnings"] = list(parsed.warnings)
    indent = None if args.indent == 0 else args.indent
    print(json.dumps(report, ensure_ascii=False, indent=indent))
    summary = report["summary"]
    if summary["violation"] > 0 or summary["confirmations"] > 0:
        print("注意：发现 %d 项违规、%d 项待人工确认（详见输出 findings/confirmations）"
              % (summary["violation"], summary["confirmations"]), file=sys.stderr)
        return EXIT_DEGRADED
    return EXIT_OK


def _run_grade(args) -> int:
    """sfc grade：方案文档 → 危大/超规模分级判定。

    退出码：0=判定完成（含"非危大"结论）；1=降级完成（参数缺失/类型未识别，
    待人工确认）；2=输入不可用（文件缺失/坏、解析失败、条款库不可用、
    --param 形式错误）。
    """
    from .parse import ParseError, parse_scheme
    from .engine.loader import KnowledgeError, load_knowledge
    from . import grading

    if not os.path.isfile(args.file):
        print("方案文件不存在：%s" % args.file, file=sys.stderr)
        return EXIT_INPUT_ERROR
    overrides = {}
    try:
        for raw in args.param:
            name, value = _parse_param_override(raw)
            overrides[name] = value
    except ValueError as exc:
        print("参数错误：%s" % exc, file=sys.stderr)
        return EXIT_INPUT_ERROR
    try:
        parsed = parse_scheme(args.file)
    except ParseError as exc:
        print("方案解析失败：%s" % exc, file=sys.stderr)
        return EXIT_INPUT_ERROR
    try:
        panorama = grading.load_panorama(args.data_dir)
    except KnowledgeError as exc:
        print("条款库不可用：%s" % exc, file=sys.stderr)
        return EXIT_INPUT_ERROR
    result = grading.judge_card(parsed.scheme_card, panorama=panorama,
                                param_overrides=overrides)
    indent = None if args.indent == 0 else args.indent
    print(json.dumps(result, ensure_ascii=False, indent=indent))
    if result.get("status") == "pending":
        print("注意：分级判定待人工确认（%s）" % result.get("note"), file=sys.stderr)
        return EXIT_DEGRADED
    return EXIT_OK


def main(argv=None) -> int:
    _force_utf8_stdio()
    parser = build_parser()
    # 未知子命令 / 坏参数：argparse 自行 SystemExit(2)，与本文件退出码口径一致
    args = parser.parse_args(argv)
    if args.command == "selfcheck":
        return _run_selfcheck()
    if args.command == "calc":
        return _run_calc(args)
    if args.command == "check":
        return _run_check(args)
    if args.command == "grade":
        return _run_grade(args)
    parser.print_help()
    return EXIT_INPUT_ERROR


if __name__ == "__main__":
    sys.exit(main())
