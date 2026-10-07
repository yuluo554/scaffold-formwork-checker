# -*- coding: utf-8 -*-
"""M3 核查规则运行器（plan/04 §4）。

- only_if 类目门控：关键词**全部**命中 scheme_card.project_type 才生效，
  跨全部 check_type 一致生效（threshold/presence/consistency/grading 同一口径）；
- 条文纪律双层拦截与引擎同口径：规则 status!=已核对，或其 limit_ref 阈值条目
  status!=已核对（经 Knowledge.threshold 第二层拦截）→ 不执行，记待人工确认；
- 参数槽位 unknown（解析失败/低置信度）→ 该规则记待人工确认，跳过而非硬判；
- verdict 只由确定性比较产生：pass / violation / triggered。
"""

import json
import os
import re

from ..consistency import check_rule as check_consistency_rule
from ..engine.loader import KnowledgeError
from ..grading import judge_card as judge_grading

CHECKS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "checks.json")

_EPS = 1e-9

_CHECK_TYPES = ("threshold", "presence", "consistency", "grading")
_OPS = ("<=", "<", ">=", ">", "==", "!=")

_FORMULA_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*\*?\s*(h|la)$")
_FORMULA_PARAM = {"h": "step", "la": "long_spacing"}


class ChecksError(Exception):
    """核查规则表不可用（缺文件/结构坏）。按输入不可用处置（CLI exit 2）。"""


class _RuleSkip(Exception):
    """单条规则本次无法执行（分支不可定/取值不可得），转待人工确认。"""

    def __init__(self, reason):
        super(_RuleSkip, self).__init__(reason)
        self.reason = reason


def load_checks_table(path=None):
    """加载核查规则表并做 schema 校验。"""
    table_path = path or CHECKS_PATH
    if not os.path.isfile(table_path):
        raise ChecksError("核查规则表缺失：%s" % table_path)
    try:
        with open(table_path, encoding="utf-8") as f:
            doc = json.load(f)
    except ValueError as exc:
        raise ChecksError("核查规则表 JSON 解析失败 %s：%s" % (table_path, exc))
    rules = doc.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ChecksError("核查规则表结构坏：rules 缺失或为空")
    seen = set()
    for rule in rules:
        for key in ("rule_id", "check_type", "param", "status"):
            if key not in rule:
                raise ChecksError("规则缺字段 %s：%r" % (key, rule.get("rule_id")))
        if rule["check_type"] not in _CHECK_TYPES:
            raise ChecksError("规则 %s check_type 非法：%r"
                              % (rule["rule_id"], rule["check_type"]))
        if rule["rule_id"] in seen:
            raise ChecksError("规则 rule_id 重复：%s" % rule["rule_id"])
        seen.add(rule["rule_id"])
        if rule["check_type"] == "threshold":
            if rule.get("op") not in _OPS:
                raise ChecksError("规则 %s op 非法：%r" % (rule["rule_id"], rule.get("op")))
            if not rule.get("limit_ref"):
                raise ChecksError("规则 %s 缺 limit_ref（限值不写死，须挂阈值表）"
                                  % rule["rule_id"])
    return doc


def _gate_passes(rule, scheme_card):
    """only_if 门控：关键词全部命中工程类型文本（AND 语义，跨 check_type 一致）。"""
    keywords = rule.get("only_if") or []
    text = scheme_card.project_type or ""
    return all(k in text for k in keywords)


def _confirmation(rule, param, reason):
    return {
        "rule_id": rule.get("rule_id"),
        "name": rule.get("name"),
        "check_type": rule.get("check_type"),
        "param": param,
        "reason": reason,
    }


def _num(x):
    s = "%.4f" % float(x)
    s = s.rstrip("0").rstrip(".")
    return s if s else "0"


def _compare(actual, op, limit):
    if op == "<=":
        return actual <= limit + _EPS
    if op == "<":
        return actual < limit + _EPS
    if op == ">=":
        return actual >= limit - _EPS
    if op == ">":
        return actual > limit - _EPS
    if op == "==":
        return abs(actual - limit) <= _EPS
    return abs(actual - limit) > _EPS  # !=


# ---- threshold 限值解析 ----


def _eval_formula(raw, scheme_card, ref):
    """阈值表参数化限值（"3h"/"3la"/"3*h"）→ 由卡内字段现算。"""
    m = _FORMULA_RE.match(raw.strip())
    if not m:
        raise _RuleSkip("阈值 %s 限值表达式 %r 无法解析" % (ref, raw))
    factor = float(m.group(1))
    field = _FORMULA_PARAM[m.group(2)]
    if not scheme_card.is_known(field):
        raise _RuleSkip("限值 %r 依赖字段 %s 未解析，待人工确认" % (raw, field))
    return factor * float(scheme_card.value(field))


def _walltie_branch(spacing_table, scheme_card):
    """表6.4.2 分支选择：排数 + 搭设高度（H≤50 双排 / H>50 双排 / 单排 H≤24）。"""
    rows = scheme_card.value("rows") if scheme_card.is_known("rows") else None
    height = scheme_card.value("build_height") if scheme_card.is_known("build_height") else None
    if rows == "double":
        if height is None:
            raise _RuleSkip("连墙件间距分支不可定：搭设高度未解析，待人工确认")
        if height > 50.0 + _EPS:
            return "双排悬挑_H>50m"
        return "双排落地_H≤50m"
    if rows == "single":
        if height is None:
            raise _RuleSkip("连墙件间距分支不可定：搭设高度未解析，待人工确认")
        if height > 24.0 + _EPS:
            raise _RuleSkip("单排架 H>24m 超出表6.4.2 覆盖范围（单排不应超过24m），待人工确认")
        return "单排_H≤24m"
    raise _RuleSkip("连墙件间距分支不可定：排数未解析，待人工确认")


def _resolve_limit(rule, scheme_card, knowledge):
    """规则限值解析：标量阈值 / 阈值表分支+参数化表达式。"""
    ref = rule["limit_ref"]
    threshold = knowledge.threshold(ref)  # 待核对/缺失 → KnowledgeError（第二层拦截）
    value = threshold["value"]
    key = rule.get("limit_key")
    if key is None:
        if isinstance(value, dict):
            raise ChecksError("阈值 %s 为分支表，规则 %s 须给 limit_key" % (ref, rule["rule_id"]))
        return float(value), ref
    if not isinstance(value, dict):
        raise ChecksError("阈值 %s 非分支表，规则 %s 不应给 limit_key" % (ref, rule["rule_id"]))
    branch_name = _walltie_branch(value, scheme_card)
    branch = value.get(branch_name)
    if branch is None or key not in branch:
        raise _RuleSkip("阈值 %s 分支 %s 缺键 %r，待人工确认" % (ref, branch_name, key))
    raw = branch[key]
    if isinstance(raw, str):
        return _eval_formula(raw, scheme_card, ref), "%s.%s.%s=%s" % (ref, branch_name, key, raw)
    return float(raw), "%s.%s.%s=%s" % (ref, branch_name, key, raw)


# ---- 各 check_type 执行 ----

def _run_threshold(rule, scheme_card, knowledge, findings, confirmations):
    param = rule["param"]
    computed = rule.get("computed")
    if computed:
        names = [n.strip() for n in computed.split("*")]
        missing = [n for n in names if not scheme_card.is_known(n)]
        if missing:
            confirmations.append(_confirmation(
                rule, param, "计算字段 %s 未解析，待人工确认" % ", ".join(missing)))
            return
        actual = 1.0
        for n in names:
            actual *= float(scheme_card.value(n))
    else:
        if not scheme_card.is_known(param):
            confirmations.append(_confirmation(
                rule, param, "参数 %s 未解析/低置信度，待人工确认" % param))
            return
        actual = float(scheme_card.value(param))
    try:
        limit, limit_source = _resolve_limit(rule, scheme_card, knowledge)
    except KnowledgeError as exc:
        confirmations.append(_confirmation(rule, param, "限值依据不可用：%s" % exc))
        return
    except _RuleSkip as exc:
        confirmations.append(_confirmation(rule, param, exc.reason))
        return
    op = rule["op"]
    ok = _compare(actual, op, limit)
    findings.append({
        "rule_id": rule["rule_id"],
        "name": rule.get("name"),
        "check_type": "threshold",
        "param": param,
        "verdict": "pass" if ok else "violation",
        "level": None if ok else rule.get("level"),
        "expr": "%s %s %s" % (_num(actual), op, _num(limit)),
        "actual": actual,
        "op": op,
        "limit_value": limit,
        "limit_source": limit_source,
        "clause_refs": rule.get("clause_refs", []),
        "advice": rule.get("advice"),
    })


def _run_presence(rule, scheme_card, findings, confirmations):
    param = rule["param"]
    if not scheme_card.is_known(param):
        confirmations.append(_confirmation(
            rule, param, "参数 %s 未解析/低置信度，待人工确认" % param))
        return
    present = bool(scheme_card.value(param))
    findings.append({
        "rule_id": rule["rule_id"],
        "name": rule.get("name"),
        "check_type": "presence",
        "param": param,
        "verdict": "pass" if present else "violation",
        "level": None if present else rule.get("level"),
        "expr": "%s 在位=%s" % (param, "是" if present else "否"),
        "clause_refs": rule.get("clause_refs", []),
        "advice": rule.get("advice"),
    })


def _run_consistency(rule, scheme_card, calcbook_card, findings, confirmations):
    kind, payload = check_consistency_rule(rule, scheme_card, calcbook_card)
    if kind == "confirmation":
        confirmations.append(payload)
    else:
        findings.append(payload)


def _run_grading_rule(rule, scheme_card, grading_result, findings, confirmations):
    require_level = rule.get("require_level")
    evidence_param = rule.get("evidence_param")
    if grading_result.get("status") == "pending":
        confirmations.append(_confirmation(
            rule, evidence_param, "分级判定待人工确认（%s），本条暂不执行"
            % grading_result.get("note")))
        return
    if grading_result.get("level") != require_level:
        findings.append({
            "rule_id": rule["rule_id"],
            "name": rule.get("name"),
            "check_type": "grading",
            "param": grading_result.get("param"),
            "verdict": "pass",
            "level": None,
            "expr": "当前分级=%s，不适用本条（要求=%s）"
                    % (grading_result.get("level"), require_level),
            "actual": grading_result.get("actual"),
            "clause_refs": rule.get("clause_refs", []),
        })
        return
    if not scheme_card.is_known(evidence_param):
        confirmations.append(_confirmation(
            rule, evidence_param,
            "方案未解析到%s关键词，待人工确认" % rule.get("evidence_label")))
        return
    evidenced = bool(scheme_card.value(evidence_param))
    findings.append({
        "rule_id": rule["rule_id"],
        "name": rule.get("name"),
        "check_type": "grading",
        "param": grading_result.get("param"),
        "evidence_param": evidence_param,
        "evidenced": evidenced,
        "verdict": "pass" if evidenced else "violation",
        "level": None if evidenced else rule.get("level"),
        "expr": "分级=%s（%s=%s）且方案%s%s" % (
            require_level, grading_result.get("param"), _num(grading_result.get("actual")),
            "已载明" if evidenced else "未载明",
            rule.get("evidence_label", "")),
        "actual": grading_result.get("actual"),
        "clause_refs": rule.get("clause_refs", []),
        "advice": rule.get("advice"),
    })


def _grading_finding(grading_result, findings, confirmations):
    """分级判定结论落为 finding（triggered=信息性触发；none=pass）。"""
    if grading_result.get("status") == "pending":
        confirmations.append({
            "rule_id": "G-grading",
            "name": "危大分级判定",
            "check_type": "grading",
            "param": (grading_result.get("unknown_params") or [None])[0],
            "reason": "危大分级待人工确认：%s" % grading_result.get("note"),
        })
        return
    findings.append({
        "rule_id": grading_result["rule_id"],
        "name": "危大分级判定（%s）" % grading_result["project_type"],
        "check_type": "grading",
        "param": grading_result.get("param"),
        "verdict": grading_result["verdict"],
        "level": None if grading_result["verdict"] == "pass" else "提示",
        "expr": "%s → %s" % (grading_result.get("cond"), grading_result["label"]),
        "actual": grading_result.get("actual"),
        "clause_refs": [grading_result["item_id"]],
        "basis": grading_result.get("basis", []),
        "advice": grading_result.get("duty"),
    })


def run_checks(scheme_card, calcbook_card, knowledge, checks_table=None):
    """核查主管线：分级判定 + 逐规则执行（门控→拦截→分派）。

    返回报告 dict：findings（含 pass）、confirmations（待人工确认）、summary。
    """
    if checks_table is None:
        checks_table = load_checks_table()
    findings = []
    confirmations = []
    grading_result = judge_grading(scheme_card)
    _grading_finding(grading_result, findings, confirmations)
    for rule in checks_table["rules"]:
        if rule.get("status") != "已核对":
            confirmations.append(_confirmation(
                rule, rule.get("param"),
                "规则 status=%s（未核对），不得执行" % rule.get("status")))
            continue
        if not _gate_passes(rule, scheme_card):
            continue
        check_type = rule["check_type"]
        if check_type == "threshold":
            _run_threshold(rule, scheme_card, knowledge, findings, confirmations)
        elif check_type == "presence":
            _run_presence(rule, scheme_card, findings, confirmations)
        elif check_type == "consistency":
            _run_consistency(rule, scheme_card, calcbook_card, findings, confirmations)
        elif check_type == "grading":
            _run_grading_rule(rule, scheme_card, grading_result, findings, confirmations)
        else:  # load_checks_table 已校验，防御分支
            raise ChecksError("未知 check_type %r" % (check_type,))
    counts = {"pass": 0, "violation": 0, "triggered": 0}
    for f in findings:
        counts[f["verdict"]] = counts.get(f["verdict"], 0) + 1
    summary = {
        "rules_total": len(checks_table["rules"]),
        "findings": len(findings),
        "pass": counts.get("pass", 0),
        "violation": counts.get("violation", 0),
        "triggered": counts.get("triggered", 0),
        "confirmations": len(confirmations),
        # all_pass=无违规（triggered 为信息性分级结论，不算违规）
        "all_pass": counts.get("violation", 0) == 0,
    }
    return {
        "scheme_card": scheme_card.to_dict(),
        "calcbook_card": calcbook_card.to_dict(),
        "grading": grading_result,
        "findings": findings,
        "confirmations": confirmations,
        "summary": summary,
    }


__all__ = ["ChecksError", "load_checks_table", "run_checks"]
