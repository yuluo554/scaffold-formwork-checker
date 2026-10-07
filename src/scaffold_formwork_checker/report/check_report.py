# -*- coding: utf-8 -*-
"""M4 核查报告导出：run_checks 报告 dict → docx（plan/04 §7）。

结构：封面（标题/来源文件/工具行）→ 核查概要 → 方案概况（参数卡+
unknown_slots+验算书卡）→ 逐项核查结果 → 违规清单（级别/建议/条款/
原文摘录）→ 危大分级结论（义务+依据摘录）→ 待人工确认项 → 解析告警
（如有）→ 免责声明（强制）。

确定性：内容无时间戳、零外链；落盘经 docx_writer.save_normalized 规范化，
同输入位级一致（tests/test_report_check.py 锁定）。原文摘录仅在传入
knowledge 时回填（查不到的条款号静默跳过，不阻塞报告生成）。
"""

from .docx_writer import (
    DISCLAIMER, TOOL_LINE, add_table, fmt_num, fmt_value, new_document,
    save_normalized,
)

_DEFAULT_TITLE = "专项施工方案核查报告"

_VERDICT_TEXT = {"pass": "通过", "violation": "违规", "triggered": "触发（信息性）"}


def _entry_rows(card_dict):
    """参数卡 dict → [参数, 取值, 单位, 置信度] 行集。"""
    rows = []
    for name, entry in (card_dict.get("entries") or {}).items():
        conf = entry.get("confidence")
        rows.append([
            name,
            fmt_value(entry.get("value")),
            entry.get("unit") or "",
            ("%.2f" % conf) if isinstance(conf, (int, float)) else "",
        ])
    return rows


def _finding_row(f):
    return [
        f.get("rule_id") or "—",
        f.get("check_type") or "—",
        _VERDICT_TEXT.get(f.get("verdict"), f.get("verdict") or "—"),
        f.get("expr") or f.get("note") or "",
        "、".join(f.get("clause_refs") or []),
    ]


def _clause_excerpt(knowledge, ref):
    """条款号 → "条款号：原文摘录"；库中不存在返回 None。"""
    if knowledge is None or not ref:
        return None
    clause = knowledge.clause(ref)
    if not clause:
        return None
    excerpt = clause.get("excerpt") or clause.get("gist") or ""
    if not excerpt:
        return None
    return "%s《%s》%s：%s" % (ref, clause.get("standard") or "",
                              clause.get("clause_no") or "", excerpt)


def _violation_section(doc, report, knowledge):
    """违规清单：级别/说明/建议/条款/原文摘录（逐项小节）。"""
    violations = [f for f in report["findings"] if f.get("verdict") == "violation"]
    if not violations:
        doc.add_paragraph("本次核查无违规项。")
        return
    add_table(doc, ["规则", "级别", "说明", "条款"], [
        [v.get("rule_id") or "—", v.get("level") or "—",
         v.get("expr") or v.get("note") or "", "、".join(v.get("clause_refs") or [])]
        for v in violations
    ])
    for v in violations:
        doc.add_heading("%s（%s）" % (v.get("rule_id"), v.get("level") or "—"), level=2)
        if v.get("name"):
            doc.add_paragraph("规则：%s" % v["name"])
        if v.get("advice"):
            doc.add_paragraph("整改建议：%s" % v["advice"])
        excerpts = []
        for ref in (v.get("clause_refs") or []):
            text = _clause_excerpt(knowledge, ref)
            if text:
                excerpts.append(text)
        if excerpts:
            doc.add_paragraph("依据摘录：" + "；".join(excerpts))


def _grading_section(doc, grading):
    """危大分级结论：结论/义务/判定条件/依据摘录（grading 自带 basis）。"""
    if grading.get("status") == "pending":
        doc.add_paragraph("分级判定待人工确认：%s" % grading.get("note", ""))
        if grading.get("unknown_params"):
            doc.add_paragraph("缺失参数：%s"
                              % ", ".join(grading["unknown_params"]))
        return
    doc.add_paragraph("结论：%s（级别 %s）" % (grading.get("label"), grading.get("level")))
    if grading.get("cond"):
        doc.add_paragraph("判定条件：%s（当前 %s=%s）"
                          % (grading["cond"], grading.get("param"),
                             fmt_num(grading["actual"]) if grading.get("actual") is not None else "—"))
    if grading.get("duty"):
        doc.add_paragraph("义务提示：%s" % grading["duty"])
    basis = grading.get("basis") or []
    if basis:
        add_table(doc, ["依据文件", "原文摘录"],
                  [[b.get("doc") or "—", b.get("excerpt") or "—"] for b in basis])


def generate_check_report(report, out_path, knowledge=None, title=None):
    """生成 docx 核查报告并落盘；返回输出路径。

    report：run_checks 返回 dict（可附 CLI 增补的 file/warnings 键）；
    knowledge：可选 Knowledge 实例（回填违规条款原文摘录）。
    """
    doc = new_document()
    summary = report.get("summary") or {}

    doc.add_heading(title or _DEFAULT_TITLE, level=0)
    doc.add_paragraph("来源文件：%s" % (report.get("file") or "—"))
    doc.add_paragraph(TOOL_LINE)

    doc.add_heading("一、核查概要", level=1)
    add_table(doc, ["项目", "数值"], [
        ["规则总数", str(summary.get("rules_total", "—"))],
        ["核查产出项", str(summary.get("findings", "—"))],
        ["通过", str(summary.get("pass", "—"))],
        ["违规", str(summary.get("violation", "—"))],
        ["分级触发（信息性）", str(summary.get("triggered", "—"))],
        ["待人工确认", str(summary.get("confirmations", "—"))],
        ["总体结论", "无违规" if summary.get("all_pass") else "存在违规，须整改复核"],
    ])

    scheme_card = report.get("scheme_card") or {}
    calcbook_card = report.get("calcbook_card") or {}

    doc.add_heading("二、方案概况与参数卡", level=1)
    if scheme_card.get("project_type"):
        doc.add_paragraph("工程类型（方案标题行）：%s" % scheme_card["project_type"])
    entry_rows = _entry_rows(scheme_card)
    if entry_rows:
        add_table(doc, ["参数", "取值", "单位", "置信度"], entry_rows)
    else:
        doc.add_paragraph("（方案卡无已解析参数）")
    if scheme_card.get("unknown_slots"):
        doc.add_paragraph("未解析/低置信度槽位（宁缺勿错，转待人工确认）：%s"
                          % ", ".join(scheme_card["unknown_slots"]))
    doc.add_paragraph("验算书取值卡：")
    cb_rows = _entry_rows(calcbook_card)
    if cb_rows:
        add_table(doc, ["参数", "取值", "单位", "置信度"], cb_rows)
    else:
        doc.add_paragraph("（未解析到验算书取值句）")

    doc.add_heading("三、逐项核查结果", level=1)
    findings = report.get("findings") or []
    if findings:
        add_table(doc, ["规则", "类型", "结果", "说明", "条款"],
                  [_finding_row(f) for f in findings])
    else:
        doc.add_paragraph("（无核查产出项）")

    doc.add_heading("四、违规清单", level=1)
    _violation_section(doc, report, knowledge)

    doc.add_heading("五、危大分级结论", level=1)
    _grading_section(doc, report.get("grading") or {})

    doc.add_heading("六、待人工确认项", level=1)
    confirmations = report.get("confirmations") or []
    if confirmations:
        add_table(doc, ["规则", "参数", "原因"], [
            [c.get("rule_id") or "—", c.get("param") or "—", c.get("reason") or ""]
            for c in confirmations
        ])
    else:
        doc.add_paragraph("（无待人工确认项）")

    warnings = report.get("warnings") or []
    if warnings:
        doc.add_heading("七、解析告警", level=1)
        for w in warnings:
            doc.add_paragraph("· " + w)

    doc.add_heading("免责声明", level=1)
    doc.add_paragraph(DISCLAIMER)

    return save_normalized(doc, out_path)


__all__ = ["generate_check_report"]
