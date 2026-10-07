# -*- coding: utf-8 -*-
"""M3 一致性检测守门（"两张皮"）。

口径（真值锁定）：两卡任一侧缺字段 → 待人工确认；|Δ|≤容差 → pass；
超容差 → verdict=violation（两方向都是非 pass），level 按安全方向：
方案实况劣于验算书（实况未被验算覆盖）→ 不合格；优于 → 提示。
"""

from scaffold_formwork_checker.consistency import check_rule
from scaffold_formwork_checker.parse.card import SchemeCard

_RULE = {"rule_id": "R-consistency-step", "name": "验算书步距取值与方案正文一致",
         "check_type": "consistency", "param": "step", "level": "不合格",
         "clause_refs": ["37号令-第十六条"]}


def _card(card_type, step):
    card = SchemeCard(card_type)
    card.set("step", step, unit="m")
    return card


def test_identical_values_pass():
    kind, f = check_rule(_RULE, _card("scheme", 1.8), _card("calcbook", 1.8))
    assert kind == "finding"
    assert f["verdict"] == "pass"
    assert f["level"] is None


def test_within_tolerance_passes():
    kind, f = check_rule(_RULE, _card("scheme", 1.8), _card("calcbook", 1.805))
    assert f["verdict"] == "pass"
    kind, f = check_rule(_RULE, _card("scheme", 1.8), _card("calcbook", 1.82))
    assert f["verdict"] == "violation"


def test_scheme_worse_than_calcbook_is_unqualified():
    """方案 1.8 / 验算书 1.5：实况未被验算覆盖 → 不合格（SY-two-sheets-01 方向）。"""
    kind, f = check_rule(_RULE, _card("scheme", 1.8), _card("calcbook", 1.5))
    assert kind == "finding"
    assert f["verdict"] == "violation"
    assert f["level"] == "不合格"
    assert f["scheme_value"] == 1.8
    assert f["calcbook_value"] == 1.5
    assert "实况未被验算覆盖" in f["impact"]
    assert "37号令-第十六条" in f["clause_refs"]


def test_scheme_better_than_calcbook_is_hint():
    """方案 1.5 / 验算书 1.8：验算偏保守 → 提示级（SY-two-sheets-02 方向）。

    真值口径：两方向 verdict 均为 violation（非 pass 进违规清单）。
    """
    kind, f = check_rule(_RULE, _card("scheme", 1.5), _card("calcbook", 1.8))
    assert f["verdict"] == "violation"
    assert f["level"] == "提示"
    assert "偏保守" in f["impact"]


def test_missing_side_becomes_confirmation():
    kind, payload = check_rule(_RULE, _card("scheme", 1.8), SchemeCard("calcbook"))
    assert kind == "confirmation"
    assert "验算书卡缺少字段 step" in payload["reason"]
    kind, payload = check_rule(_RULE, SchemeCard("scheme"), _card("calcbook", 1.8))
    assert kind == "confirmation"
    assert "方案卡缺少字段 step" in payload["reason"]


def test_direction_sign_respected_for_negative_worse():
    """worse_sign=-1 的参数：取值越小越危险（防御性口径验证）。"""
    rule = dict(_RULE, rule_id="R-consistency-x", param="step", worse_sign=-1)
    kind, f = check_rule(rule, _card("scheme", 1.5), _card("calcbook", 1.8))
    assert f["verdict"] == "violation" and f["level"] == "不合格"
    kind, f = check_rule(rule, _card("scheme", 1.8), _card("calcbook", 1.5))
    assert f["verdict"] == "violation" and f["level"] == "提示"
