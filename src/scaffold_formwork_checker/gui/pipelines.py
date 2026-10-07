# -*- coding: utf-8 -*-
"""GUI 业务管线（零 Qt 依赖）：五页签共用的引擎编排层。

纪律（HANDOFF-M5 口径 17）：GUI 只消费引擎 API——本模块与 CLI（cli.py）
同款函数调用（parse/rules/consistency/grading/bench/report + engine），
不复制任何判定逻辑；页签（Qt 层）只做表单采集与结果展示。
异常面向用户：CardError/KnowledgeError/ParseError/ChecksError 的消息直接可读，
由页签捕获后经 notify 信号展示（不弹模态框，offscreen 测试安全）。
"""

from .. import bench
from ..consistency import check_rule as check_consistency_rule
from ..engine import CardError, KnowledgeError, detect_module, load_knowledge, run_calc
from ..engine.loader import find_data_dir
from ..grading import judge_card, load_panorama
from ..parse import ParseError, parse_scheme
from ..report import generate_calc_report, generate_check_report
from ..rules import ChecksError, load_checks_table, run_checks

__all__ = [
    "CardError", "ChecksError", "KnowledgeError", "ParseError",
    "resolved_data_dir", "run_calc_pipeline", "run_check_pipeline",
    "run_consistency_pipeline", "run_grading_pipeline", "run_bench_pipeline",
    "export_calc_report", "export_check_report",
]


def resolved_data_dir(data_dir=None):
    """当前生效的数据目录（状态栏展示用）；未找到返回 None。"""
    return find_data_dir(data_dir)


def run_calc_pipeline(card_data, module_id=None, data_dir=None):
    """验算：参数卡 dict → CalcResult（模块缺省按内容自动识别）。"""
    knowledge = load_knowledge(data_dir)
    mid = module_id or detect_module(card_data if isinstance(card_data, dict) else {})
    return run_calc(mid, card_data, knowledge)


def run_check_pipeline(path, data_dir=None):
    """方案核查：docx/pdf → run_checks 报告（含参数卡回显与解析告警）。"""
    parsed = parse_scheme(path)
    knowledge = load_knowledge(data_dir)
    checks_table = load_checks_table()
    report = run_checks(parsed.scheme_card, parsed.calcbook_card, knowledge,
                        checks_table)
    report = dict(report)
    report["tool"] = "sfc gui"
    report["file"] = path
    report["warnings"] = list(parsed.warnings)
    report["scheme_card"] = parsed.scheme_card.to_dict()
    return report


def run_consistency_pipeline(path_a, path_b=None, data_dir=None):
    """一致性（两张皮）：方案文件（必选）+ 验算书文件（可选，缺省取同一
    文档内的验算书章节卡）→ 逐条一致性规则比对 → 差异 findings。

    只消费 checks.json 的 consistency 规则与 consistency.check_rule，
    定级口径与 CLI 完全同源（劣于=不合格、优于=提示，均记 violation）。
    """
    parsed_a = parse_scheme(path_a)
    scheme = parsed_a.scheme_card
    if path_b:
        calcbook = parse_scheme(path_b).calcbook_card
    else:
        calcbook = parsed_a.calcbook_card
    checks_table = load_checks_table()
    findings = []
    confirmations = []
    for rule in checks_table["rules"]:
        if rule.get("check_type") != "consistency":
            continue
        if rule.get("status") != "已核对":
            confirmations.append({
                "rule_id": rule.get("rule_id"),
                "check_type": "consistency",
                "param": rule.get("param"),
                "reason": "规则 status=%s（未核对），不得执行" % rule.get("status"),
            })
            continue
        kind, payload = check_consistency_rule(rule, scheme, calcbook)
        (findings if kind == "finding" else confirmations).append(payload)
    return {
        "findings": findings,
        "confirmations": confirmations,
        "scheme_doc": scheme.doc_name,
        "calcbook_doc": calcbook.doc_name if path_b else None,
    }


def run_grading_pipeline(path, overrides=None, data_dir=None):
    """危大分级：方案文档 + 显式参数覆盖 → judge_card 结果。"""
    parsed = parse_scheme(path)
    panorama = load_panorama(data_dir)
    return judge_card(parsed.scheme_card, panorama=panorama,
                      param_overrides=dict(overrides or {}))


def run_bench_pipeline(data_dir=None):
    """内置基准：三套件一条管线跑完（零 API、离线、确定性）。"""
    return bench.run_all(data_dir)


def export_calc_report(card_data, result, output, title=None):
    """验算书导出：与 sfc report calc 同一渲染器（report/ 纯渲染器纪律）。"""
    generate_calc_report(card_data, result, output, title=title)


def export_check_report(report, output, data_dir=None, title=None):
    """核查报告导出：与 sfc report check 同一渲染器（条款原文回填同口径）。"""
    knowledge = load_knowledge(data_dir)
    generate_check_report(report, output, knowledge=knowledge, title=title)
