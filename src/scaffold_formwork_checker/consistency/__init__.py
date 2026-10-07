# -*- coding: utf-8 -*-
"""M3 一致性检测（"两张皮"，plan/04 §5）。

输入：方案参数卡 + 验算书取值卡（同一 schema）。仅比对两侧都存在的字段；
数值容差=字段定义（长度类 0.01m）；差异按安全方向定级：

- 方案实况劣于验算书取值（实况未被验算覆盖，危险方向）→ 不合格；
- 方案实况优于验算书取值（验算偏保守）→ 提示；
- 两种方向 verdict 均为 violation（非 pass，进违规清单）——真值口径
  （SY-two-sheets-01/-02 两方向均判 violation），方向只决定 level。

两侧任一缺失字段 → 待人工确认（confirmation），不硬判。
"""

# 容差=字段定义：长度类 0.01m；搭设高度允许 0.05m（概况表述舍入）
TOLERANCES = {
    "step": 0.01,
    "long_spacing": 0.01,
    "cross_spacing": 0.01,
    "wall_tie_v": 0.01,
    "wall_tie_h": 0.01,
    "build_height": 0.05,
}
DEFAULT_TOLERANCE = 0.01

# 安全方向符号：+1=取值越大越危险（几何/荷载类）；-1=取值越小越危险
WORSE_SIGN = {
    "step": +1,
    "long_spacing": +1,
    "cross_spacing": +1,
    "wall_tie_v": +1,
    "wall_tie_h": +1,
    "build_height": +1,
}

# 差异影响的验算模块（报告回溯用）
PARAM_MODULES = {
    "step": "M-1/M-2/M-6 立杆稳定（计算长度）",
    "long_spacing": "M-1/M-2/M-3（纵距传力）",
    "cross_spacing": "M-1/M-2/M-3（横距传力）",
    "wall_tie_v": "M-4 连墙件",
    "wall_tie_h": "M-4 连墙件",
    "build_height": "M-1/M-2 立杆稳定",
}

_EPS = 1e-9


def check_rule(rule, scheme_card, calcbook_card):
    """执行单条一致性规则。

    返回 ("finding", dict) 或 ("confirmation", dict)；由 rules 运行器收集。
    """
    param = rule["param"]
    if not scheme_card.is_known(param) or not calcbook_card.is_known(param):
        missing = [name for name, card in (("方案卡", scheme_card),
                                           ("验算书卡", calcbook_card))
                   if not card.is_known(param)]
        return ("confirmation", {
            "rule_id": rule["rule_id"],
            "check_type": "consistency",
            "param": param,
            "reason": "%s缺少字段 %s，待人工确认" % ("与".join(missing), param),
        })
    scheme_value = float(scheme_card.value(param))
    calcbook_value = float(calcbook_card.value(param))
    tolerance = float(rule.get("tolerance", TOLERANCES.get(param, DEFAULT_TOLERANCE)))
    delta = calcbook_value - scheme_value
    base = {
        "rule_id": rule["rule_id"],
        "name": rule.get("name"),
        "check_type": "consistency",
        "param": param,
        "scheme_value": scheme_value,
        "calcbook_value": calcbook_value,
        "delta": delta,
        "tolerance": tolerance,
        "clause_refs": rule.get("clause_refs", []),
        "advice": rule.get("advice"),
    }
    if abs(delta) <= tolerance + _EPS:
        base["verdict"] = "pass"
        base["level"] = None
        base["note"] = "两卡取值一致（容差 %.3f 内）" % tolerance
        return ("finding", base)
    worse_sign = int(rule.get("worse_sign", WORSE_SIGN.get(param, +1)))
    scheme_worse = (scheme_value - calcbook_value) * worse_sign > 0
    module = PARAM_MODULES.get(param, "相关验算模块")
    if scheme_worse:
        base["level"] = "不合格"
        base["impact"] = "方案实况劣于验算书取值，实况未被验算覆盖（影响：%s）" % module
    else:
        base["level"] = "提示"
        base["impact"] = "验算书取值劣于方案实况（验算偏保守），两卡仍需统一（影响：%s）" % module
    base["verdict"] = "violation"
    base["note"] = "方案正文与验算书取值不一致；按影响方向定级（劣于=不合格）"
    base["expr"] = "方案=%s vs 验算书=%s（|Δ|=%.3f > 容差 %.3f）" % (
        _fmt(scheme_value), _fmt(calcbook_value), abs(delta), tolerance)
    return ("finding", base)


def _fmt(x):
    s = "%.3f" % float(x)
    s = s.rstrip("0").rstrip(".")
    return s if s else "0"
