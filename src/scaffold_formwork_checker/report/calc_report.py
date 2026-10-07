# -*- coding: utf-8 -*-
"""M4 验算书导出：参数卡 + CalcResult → docx（plan/04 §7）。

结构：封面（标题/模块/工具行）→ 参数卡表 → 逐项验算（表达式/代入/比值/
限值/结论/条款依据）→ 中间量表 → 结论汇总 → 签署栏（手填）→ 免责声明
（强制）。blocked 结果不渲染任何计算数值，仅载说明（条文纪律）。

确定性：内容无时间戳、零外链；落盘经 docx_writer.save_normalized 规范化，
同输入位级一致（tests/test_report_calc.py 锁定）。
"""

from ..engine import MODULE_NAMES
from .docx_writer import (
    DISCLAIMER, TOOL_LINE, add_table, fmt_num4, fmt_value, new_document,
    save_normalized,
)

_DEFAULT_TITLE = "安全验算书"


def _flatten_rows(obj, prefix=""):
    """参数卡拍平为两列表（嵌套 dict 用点号路径，list 分号连接）。"""
    rows = []
    for key, value in obj.items():
        name = prefix + key
        if isinstance(value, dict):
            rows.extend(_flatten_rows(value, name + "."))
        else:
            rows.append((name, fmt_value(value)))
    return rows


def _check_rows(result):
    rows = []
    for c in result["checks"]:
        rows.append([
            c["item"],
            c.get("expr", ""),
            c.get("substituted", ""),
            fmt_num4(c["ratio"]),
            fmt_num4(c["limit"]),
            "通过" if c["verdict"] == "pass" else "不满足",
            "、".join(c.get("clause_refs") or []),
        ])
    return rows


def _conclusion_text(result):
    if result.get("status") == "blocked":
        return "本模块未执行验算：%s" % result.get("status_note", "")
    checks = result["checks"]
    fail = [c for c in checks if c["verdict"] != "pass"]
    if not fail:
        return ("全部 %d 项检查通过（比值≤1.0），按所依据规范满足要求；"
                "结论详见上表，条款依据逐项在列。" % len(checks))
    lines = ["%d/%d 项检查不满足（比值>1.0），须调整参数后重新验算：" % (len(fail), len(checks))]
    for c in fail:
        lines.append("· %s：比值 %s > 限值 %s（%s）"
                     % (c["item"], fmt_num4(c["ratio"]), fmt_num4(c["limit"]),
                        "、".join(c.get("clause_refs") or [])))
    return "\n".join(lines)


def generate_calc_report(card_data, result, out_path, title=None):
    """生成 docx 验算书并落盘；返回输出路径。

    card_data：引擎参数卡 dict（与 sfc calc 输入一致）；
    result：run_calc 的 CalcResult dict（含 status/checks/detail）。
    """
    doc = new_document()
    module_id = result.get("module_id", "")
    module_name = MODULE_NAMES.get(module_id, module_id)
    doc.add_heading(title or _DEFAULT_TITLE, level=0)
    doc.add_paragraph("验算模块：%s（%s）" % (module_name, module_id))
    doc.add_paragraph(TOOL_LINE)

    doc.add_heading("一、参数卡", level=1)
    if isinstance(card_data, dict) and card_data:
        add_table(doc, ["参数", "取值"], _flatten_rows(card_data))
    else:
        doc.add_paragraph("（参数卡为空）")

    doc.add_heading("二、逐项验算", level=1)
    if result.get("status") == "blocked":
        doc.add_paragraph("本模块未执行验算：%s" % result.get("status_note", ""))
        doc.add_paragraph("依赖的规范条目未经原文核对（status≠已核对），"
                          "按条文纪律拒绝进入计算路径；核对后重试。")
    else:
        add_table(doc,
                  ["检查项", "表达式", "代入", "比值", "限值", "结论", "条款依据"],
                  _check_rows(result))

    doc.add_heading("三、中间量", level=1)
    detail = result.get("detail") or {}
    if detail:
        add_table(doc, ["中间量", "数值"],
                  [[k, fmt_num4(v) if isinstance(v, (int, float))
                    else fmt_value(v)] for k, v in sorted(detail.items())])
    else:
        doc.add_paragraph("（无中间量）")

    doc.add_heading("四、结论汇总", level=1)
    doc.add_paragraph(_conclusion_text(result))

    doc.add_heading("五、签署栏（手填）", level=1)
    add_table(doc, ["编制", "审核", "批准", "日期"],
              [["", "", "", ""]])
    doc.add_paragraph("本栏由编制/审核/批准人手工签署；工具不代填任何签署信息与日期。")

    doc.add_heading("六、免责声明", level=1)
    doc.add_paragraph(DISCLAIMER)

    return save_normalized(doc, out_path)


__all__ = ["generate_calc_report"]
