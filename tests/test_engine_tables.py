# -*- coding: utf-8 -*-
"""M2 查表模块守门：转录矩阵与 thresholds.json 登记锚点逐一对账 + 口径锁定。"""

import json
import os

from scaffold_formwork_checker.engine import tables

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAUSES_DIR = os.path.join(REPO_ROOT, "data", "knowledge", "clauses")


def _threshold(threshold_id):
    with open(os.path.join(CLAUSES_DIR, "thresholds.json"), encoding="utf-8") as f:
        for t in json.load(f)["thresholds"]:
            if t["threshold_id"] == threshold_id:
                return t
    raise AssertionError(threshold_id)


def test_verify_anchors_passes():
    assert tables.verify_anchors() is True


def test_phi_table_complete_251_entries():
    assert len(tables.PHI_TABLE) == 251
    for lam in range(251):
        assert 0 < tables.PHI_TABLE[lam] <= 1.0, lam


def test_phi_table_monotonic_non_increasing():
    for lam in range(250):
        assert tables.PHI_TABLE[lam] >= tables.PHI_TABLE[lam + 1], lam


def test_phi_ceil_lookup_convention():
    """决策 #18：λ=ceil(l0/i) 向上取整查档，禁插值。"""
    assert tables.phi_of(196.132) == tables.PHI_TABLE[197] == 0.186
    assert tables.phi_of(84.9) == tables.PHI_TABLE[85] == 0.692
    assert tables.phi_of(250.0) == 0.117


def test_phi_over_250_formula():
    """λ>250 用原文表注公式 φ=7320/λ²。"""
    assert abs(tables.phi_of(251.0) - 7320.0 / (251.0 ** 2)) < 1e-15
    assert abs(tables.phi_of(300.0) - 7320.0 / (300.0 ** 2)) < 1e-15
    assert tables.phi_of(260.0) < tables.PHI_TABLE[250]


def test_gk_anchors_match_thresholds_ledger():
    """表A.0.1 锚点_双排 与 thresholds.json T-JGJ130-gk-table 逐格对账。"""
    anchors = _threshold("T-JGJ130-gk-table")["value"]["锚点_双排"]
    for key, expect in anchors.items():
        h_str, la_str = key.replace("h=", "").replace("la=", "").split(",")
        got = tables.gk_of(float(h_str), float(la_str), "double")
        assert abs(got - expect) < 1e-9, (key, got, expect)


def test_gk_interpolation_domain():
    """表A.0.1 表注：表内中间值可按线性插入计算；域外拒收。"""
    from scaffold_formwork_checker.engine.tables import TableLookupError
    v = tables.gk_of(1.65, 1.65, "double")
    assert min(0.1202, 0.1295, 0.1389) < v < max(0.1336, 0.1444, 0.1552)
    for h, la in ((1.0, 1.5), (2.5, 1.5), (1.8, 1.0), (1.8, 2.5)):
        try:
            tables.gk_of(h, la, "double")
        except TableLookupError:
            pass
        else:
            raise AssertionError(("域外未拒收", h, la))


def test_mu_table_matches_thresholds_ledger():
    """表5.2.8 全档与 thresholds.json T-JGJ130-mu-coef 对账；无插值注→精确匹配。"""
    value = _threshold("T-JGJ130-mu-coef")["value"]
    zh_to_enum = {"二步三跨": "two_step_three_span", "三步三跨": "three_step_three_span"}
    for lb_str, expect in value["双排_连墙件二步三跨"].items():
        lb = float(lb_str.replace("lb=", ""))
        assert tables.mu_of("double", "two_step_three_span", lb) == expect
    for lb_str, expect in value["双排_连墙件三步三跨"].items():
        lb = float(lb_str.replace("lb=", ""))
        assert tables.mu_of("double", "three_step_three_span", lb) == expect
    for tie_zh, expect in value["单排_lb≤1.50"].items():
        assert tables.mu_of("single", zh_to_enum[tie_zh], 1.2) == expect


def test_k_length_add_matches_ledger():
    """k=1.155 与 T-JGJ130-mu-coef verify 注对账。"""
    assert "1.155" in _threshold("T-JGJ130-mu-coef")["verify"]
    assert tables.K_LENGTH_ADD == 1.155


def test_m6_step_max_matches_ledger():
    """JGJ162 立柱最大步距 1.8m 与 T-JGJ162-column-step 对账。"""
    assert float(_threshold("T-JGJ162-column-step")["value"]) == tables.M6_STEP_MAX_M == 1.8


def test_steel_e_matches_ledger():
    assert "2.06" in _threshold("T-JGJ130-steel-design")["condition"]
    assert tables.STEEL_E == 206000.0


def test_deflection_limit_structure_matches_ledger():
    """[v]=min(l/150, 10mm) 与 T-JGJ130-deflection-limits 值串对账。"""
    value = _threshold("T-JGJ130-deflection-limits")["value"]["脚手板及纵横水平杆"]
    assert "l/150" in value and "10" in value
