# -*- coding: utf-8 -*-
"""M3 核查规则守门：规则表结构 / 三级判定 / only_if 门控跨类目隔离（M3 DoD ③）/
待核对双层拦截 / 限值解析（表6.4.2 分支与 3h 参数化限值）。
"""

import json
import os

import pytest

from scaffold_formwork_checker.engine.loader import Knowledge, load_knowledge
from scaffold_formwork_checker.parse.card import SchemeCard
from scaffold_formwork_checker.rules import (
    CHECKS_PATH,
    ChecksError,
    load_checks_table,
    run_checks,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")


def _knowledge():
    return load_knowledge(DATA_DIR)


_LENGTH_FIELDS = ("step", "long_spacing", "cross_spacing", "wall_tie_v",
                  "wall_tie_h", "build_height")


def _scaffold_card(project_type="某工程 落地式扣件钢管脚手架专项施工方案", **entries):
    card = SchemeCard("scheme")
    card.project_type = project_type
    card.category = "coupler_steel_pipe_scaffold"
    defaults = {
        "build_height": 12.0, "step": 1.5, "long_spacing": 1.5,
        "cross_spacing": 1.05, "wall_tie": "two_step_three_span",
        "wall_tie_v": 3.0, "wall_tie_h": 4.5, "rows": "double",
        "scissor_brace": True, "expert_review": False, "special_plan": True,
    }
    defaults.update(entries)
    for name, value in defaults.items():
        card.set(name, value, unit="m" if name in _LENGTH_FIELDS else None)
    return card


def _empty_calcbook():
    return SchemeCard("calcbook")


def _finding(report, rule_id):
    for f in report["findings"]:
        if f["rule_id"] == rule_id:
            return f
    return None


def _run(card, calcbook=None, knowledge=None):
    return run_checks(card, calcbook or _empty_calcbook(),
                      knowledge or _knowledge(), load_checks_table())


# ---- 规则表结构 ----

def test_checks_table_schema_valid():
    table = load_checks_table()
    types = {r["check_type"] for r in table["rules"]}
    assert types == {"threshold", "presence", "consistency", "grading"}
    with open(CHECKS_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    assert len(raw["rules"]) == 12


def test_checks_table_rejects_hardcoded_limits(tmp_path):
    """limit_ref 必须挂阈值表：缺 limit_ref 的 threshold 规则拒收。"""
    bad = {"rules": [{"rule_id": "X", "check_type": "threshold", "param": "step",
                      "op": "<=", "limit_ref": "", "status": "已核对"}]}
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ChecksError):
        load_checks_table(str(path))


# ---- threshold 规则与限值解析 ----

def test_step_over_fires_both_step_rules():
    report = _run(_scaffold_card(step=2.4))
    f1 = _finding(report, "R-step-limit")
    f2 = _finding(report, "R-step-limit-20")
    assert f1["verdict"] == "violation" and f1["limit_value"] == 1.8
    assert f1["actual"] == 2.4 and f1["level"] == "不合格"
    assert f2["verdict"] == "violation" and f2["limit_value"] == 2.0


def test_step_within_limit_passes():
    report = _run(_scaffold_card(step=1.8))
    assert _finding(report, "R-step-limit")["verdict"] == "pass"
    assert _finding(report, "R-step-limit-20")["verdict"] == "pass"


def test_walltie_vspacing_parametric_limit_3h():
    """限值=3h 随步距现算（表6.4.2 参数化限值）。"""
    report = _run(_scaffold_card(step=1.5, wall_tie_v=6.0))
    f = _finding(report, "R-walltie-vspacing")
    assert f["verdict"] == "violation"
    assert f["limit_value"] == 4.5  # 3×1.5
    report = _run(_scaffold_card(step=1.8, wall_tie_v=5.5))
    assert _finding(report, "R-walltie-vspacing")["limit_value"] == 5.4  # 3×1.8


def test_walltie_branch_switches_at_height_50():
    """同一实际取值跨 H=50 边界：限值档由 3h(4.5) 切到 2h(3.0)，判定翻转。"""
    report = _run(_scaffold_card(step=1.5, wall_tie_v=3.2, build_height=50.0))
    f = _finding(report, "R-walltie-vspacing")
    assert f["verdict"] == "pass" and f["limit_value"] == 4.5
    report = _run(_scaffold_card(step=1.5, wall_tie_v=3.2, build_height=50.1))
    f = _finding(report, "R-walltie-vspacing")
    assert f["verdict"] == "violation" and f["limit_value"] == 3.0  # 2×1.5


def test_walltie_area_computed_param():
    report = _run(_scaffold_card(step=1.5, wall_tie_v=9.0, wall_tie_h=4.5))
    f = _finding(report, "R-walltie-area")
    assert f["verdict"] == "violation"
    assert f["actual"] == 40.5 and f["limit_value"] == 40.0


def test_walltie_hspacing_passes_at_3la():
    report = _run(_scaffold_card(step=1.5, wall_tie_h=4.5))
    assert _finding(report, "R-walltie-hspacing")["verdict"] == "pass"
    report = _run(_scaffold_card(step=1.5, wall_tie_h=4.6))
    f = _finding(report, "R-walltie-hspacing")
    assert f["verdict"] == "violation" and f["limit_value"] == 4.5


def test_presence_brace_missing_violation_level():
    report = _run(_scaffold_card(scissor_brace=False))
    f = _finding(report, "R-brace-presence")
    assert f["verdict"] == "violation" and f["level"] == "不合格"
    report = _run(_scaffold_card(scissor_brace=True))
    assert _finding(report, "R-brace-presence")["verdict"] == "pass"


# ---- only_if 门控跨 check_type 隔离（M3 DoD ③）----

def test_gate_excludes_cantilever_from_landed_step_rules():
    """悬挑式工程：步距常用档规则（落地式门控）被隔离。"""
    card = _scaffold_card(project_type="某工程 悬挑式扣件钢管脚手架专项施工方案", step=2.4)
    report = _run(card)
    assert _finding(report, "R-step-limit") is None
    assert _finding(report, "R-step-limit-20") is None


def test_gate_excludes_scaffold_rules_for_formwork_project():
    """模板支撑工程：扣件架规则全部隔离，模板支架步距规则生效。"""
    card = _scaffold_card(project_type="某工程 混凝土模板支撑工程专项施工方案", step=2.0)
    card.category = "formwork_support"
    report = _run(card)
    for rule_id in ("R-step-limit", "R-step-limit-20", "R-walltie-vspacing",
                    "R-brace-presence"):
        assert _finding(report, rule_id) is None, rule_id
    f = _finding(report, "R-formwork-step-limit")
    assert f["verdict"] == "violation" and f["limit_value"] == 1.8


def test_gate_excludes_formwork_rule_for_scaffold_project():
    card = _scaffold_card(step=2.4)
    report = _run(card)
    assert _finding(report, "R-formwork-step-limit") is None


def test_gate_applies_to_presence_type_too():
    """门控对 presence 类同样生效：悬挑工程无剪刀撑声明不触发落地架规则。"""
    card = _scaffold_card(project_type="碗扣式钢管脚手架专项施工方案",
                          scissor_brace=False)
    report = _run(card)
    assert _finding(report, "R-brace-presence") is None


# ---- grading 类规则（分级联动）----

def test_grading_expert_review_rule_fires_for_chaoguimo():
    card = _scaffold_card(build_height=56.0, expert_review=False)
    report = _run(card)
    f = _finding(report, "R-grading-expert-review")
    assert f["verdict"] == "violation"
    assert f["level"] == "严重"
    assert f["actual"] == 56.0
    assert "37号令-第十二条" in f["clause_refs"]
    # 分级触发项同在
    g = _finding(report, "G-pan-luodi-50")
    assert g["verdict"] == "triggered"
    assert report["summary"]["violation"] >= 1


def test_grading_expert_review_passes_when_documented():
    card = _scaffold_card(build_height=56.0, expert_review=True)
    report = _run(card)
    assert _finding(report, "R-grading-expert-review")["verdict"] == "pass"


def test_grading_rules_inapplicable_below_level():
    card = _scaffold_card(build_height=12.0)
    report = _run(card)
    assert _finding(report, "R-grading-expert-review")["verdict"] == "pass"
    assert _finding(report, "R-grading-special-plan")["verdict"] == "pass"


def test_grading_special_plan_rule_fires_for_weida_without_plan():
    card = _scaffold_card(build_height=30.0, special_plan=False)
    report = _run(card)
    f = _finding(report, "R-grading-special-plan")
    assert f["verdict"] == "violation" and f["level"] == "不合格"


# ---- 待核对双层拦截（条文纪律，与引擎同口径）----

def test_unverified_rule_is_skipped_with_confirmation():
    knowledge = _knowledge()
    table = load_checks_table()
    # 构造 status=待核对 的规则副本（不落盘）
    tampered = json.loads(json.dumps(table))
    tampered["rules"][0]["status"] = "待核对"
    card = _scaffold_card(step=2.4)
    report = run_checks(card, _empty_calcbook(), knowledge, tampered)
    f = _finding(report, "R-step-limit")
    assert f is None
    conf = [c for c in report["confirmations"] if c["rule_id"] == "R-step-limit"]
    assert conf and "待核对" in conf[0]["reason"]


def test_unverified_threshold_entry_blocks_rule():
    """limit_ref 指向的阈值条目待核对 → 第二层拦截（Knowledge.threshold 抛错）。"""
    data = json.loads(json.dumps({"thresholds": [
        {"threshold_id": "T-FAKE-step", "param": "step_max", "op": "<=",
         "value": 1.8, "unit": "m", "condition": "x", "clause_ref": "JGJ130-6.1.1",
         "status": "待核对", "verify": None}]}, ensure_ascii=False))
    knowledge = Knowledge(DATA_DIR)
    knowledge._threshold_by_id["T-FAKE-step"] = data["thresholds"][0]
    table = json.loads(json.dumps(load_checks_table()))
    table["rules"] = [{
        "rule_id": "R-fake-step", "name": "x", "only_if": ["扣件", "落地式"],
        "check_type": "threshold", "param": "step", "op": "<=",
        "limit_ref": "T-FAKE-step", "level": "不合格",
        "clause_refs": ["JGJ130-6.1.1"], "status": "已核对"}]
    report = run_checks(_scaffold_card(step=2.4), _empty_calcbook(),
                        knowledge, table)
    assert _finding(report, "R-fake-step") is None
    conf = [c for c in report["confirmations"] if c["rule_id"] == "R-fake-step"]
    assert conf and "不可用" in conf[0]["reason"]


def test_missing_limit_ref_entry_blocks_rule():
    """limit_ref 指向不存在的阈值条目 → 拦截（不静默放行）。"""
    table = json.loads(json.dumps(load_checks_table()))
    table["rules"] = [{
        "rule_id": "R-missing-ref", "check_type": "threshold", "param": "step",
        "op": "<=", "limit_ref": "T-NO-SUCH-ENTRY", "level": "不合格",
        "clause_refs": ["X"], "status": "已核对", "only_if": []}]
    report = run_checks(_scaffold_card(step=2.4), _empty_calcbook(),
                        _knowledge(), table)
    conf = [c for c in report["confirmations"] if c["rule_id"] == "R-missing-ref"]
    assert conf


def test_missing_branch_params_become_confirmation():
    """排数未解析 → 表6.4.2 分支不可定 → 待人工确认（不猜分支）。"""
    card = _scaffold_card()
    card.unknown_slots.append("rows")
    card.entries.pop("rows")
    report = _run(card)
    conf = [c for c in report["confirmations"] if c["rule_id"] == "R-walltie-vspacing"]
    assert conf and "分支" in conf[0]["reason"]
