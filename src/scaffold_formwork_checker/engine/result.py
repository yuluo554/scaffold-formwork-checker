# -*- coding: utf-8 -*-
"""M2 验算结果构造：CalcResult 契约（plan/04 §3）。

CalcResult = {
  "module_id": str,
  "status": "ok" | "blocked",
  "status_note": str,          # blocked 时为"不可验算（依据未核对）：…"
  "checks": [ {item, expr, substituted, ratio, limit, verdict, clause_refs}, ... ],
  "warnings": [str, ...],
  "detail": {...}              # 中间量（与算例真值库 expect.intermediate 同名对齐）
}

verdict 只由确定性比较产生：ratio <= 1.0 → pass，否则 fail。
"""


def make_check(item, expr, substituted, ratio, limit, clause_refs):
    ratio = float(ratio)
    return {
        "item": item,
        "expr": expr,
        "substituted": substituted,
        "ratio": ratio,
        "limit": float(limit),
        "verdict": "pass" if ratio <= 1.0 else "fail",
        "clause_refs": list(clause_refs),
    }


def make_result(module_id, checks, detail=None, warnings=None):
    return {
        "module_id": module_id,
        "status": "ok",
        "status_note": "",
        "checks": checks,
        "warnings": list(warnings or []),
        "detail": dict(detail or {}),
    }


def blocked_result(module_id, unverified_ids):
    """依赖条目未核对 → 整模块拒绝运行（不带任何计算结果）。"""
    return {
        "module_id": module_id,
        "status": "blocked",
        "status_note": "不可验算（依据未核对）：%s" % ", ".join(unverified_ids),
        "checks": [],
        "warnings": [],
        "detail": {},
    }
