# -*- coding: utf-8 -*-
"""M2 参数卡拒收（M2 DoD ④：合法性范围校验在卡片构造时执行）
与参数扫描回归（M2 DoD ②：关键参数扫描锁定单调性与边界）。
"""

import copy
import json
import os

import pytest

from scaffold_formwork_checker.engine import CardError, load_knowledge, run_calc

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_M1 = {
    "category": "coupler_steel_pipe_scaffold", "rows": "double",
    "build_height_m": 12.0, "step_m": 1.8, "long_spacing_m": 1.5,
    "cross_spacing_m": 1.05, "wall_tie": "two_step_three_span",
    "pipe_spec": "48.3x3.6", "steel_grade": "Q235A", "wind": "不组合",
    "loads": {"gk_struct_kN_per_m": 0.1295, "board_kN_per_m2": 0.3,
              "board_layers": 2, "rail_kN_per_m": 0.16,
              "safety_net_kN_per_m2": 0.01, "live_kN_per_m2": 2.0},
}


@pytest.fixture(scope="module")
def knowledge():
    return load_knowledge(os.path.join(REPO_ROOT, "data"))


# ---- 非法拒收 ----

@pytest.mark.parametrize("mutate,why", [
    (lambda c: c.update(step_m=0), "步距为零"),
    (lambda c: c.update(step_m=-1.8), "步距为负"),
    (lambda c: c.update(long_spacing_m=0), "纵距为零"),
    (lambda c: c.update(cross_spacing_m=-1.05), "横距为负"),
    (lambda c: c.update(build_height_m=0), "搭设高度为零"),
    (lambda c: c["loads"].update(live_kN_per_m2=-2.0), "施工荷载为负"),
    (lambda c: c["loads"].update(board_kN_per_m2=-0.3), "脚手板荷载为负"),
    (lambda c: c["loads"].update(board_layers=-1), "脚手板层数为负"),
    (lambda c: c["loads"].update(board_layers=1.5), "脚手板层数非整数"),
    (lambda c: c["loads"].update(gk_struct_kN_per_m=0), "gk 为零"),
    (lambda c: c.update(wall_tie="four_step_four_span"), "连墙件布置坏枚举"),
    (lambda c: c.update(pipe_spec="48.3x2.0"), "暂不支持的钢管规格"),
    (lambda c: c.update(rows="triple"), "排数坏枚举"),
    (lambda c: c.pop("build_height_m"), "缺搭设高度"),
    (lambda c: c.pop("wall_tie"), "缺连墙件布置"),
    (lambda c: c.pop("loads"), "缺荷载"),
    (lambda c: c["loads"].pop("live_kN_per_m2"), "缺施工荷载"),
    (lambda c: c.update(step_m=float("nan")), "非有限数值"),
    (lambda c: c.update(step_m="1.8"), "数值传字符串"),
    (lambda c: c.update(wind={"w0_kN_per_m2": 0.4}), "M-1 卡混入组合风对象"),
])
def test_m1_invalid_cards_rejected(mutate, why, knowledge):
    card = copy.deepcopy(BASE_M1)
    mutate(card)
    with pytest.raises(CardError):
        run_calc("M-1", card, knowledge)


def test_m6_step_above_code_limit_flagged(knowledge):
    """M-6 步距超 1.8m：可计算但带规范限值 warning（构造整改归核查模块）。"""
    card = {
        "category": "formwork_support", "slab_thickness_m": 0.12, "story_height_m": 3.9,
        "step_m": 1.9, "pole_spacing_m": [1.0, 1.0], "pipe_spec": "48.3x3.6",
        "wind": "不组合",
        "loads": {"g1k_kN_per_m2": 0.75, "concrete_kN_per_m3": 24.0,
                  "rebar_kN_per_m3_slab": 1.1, "q1k_kN_per_m2": 1.0},
    }
    result = run_calc("M-6", card, knowledge)
    assert result["status"] == "ok"
    assert any("1.8" in w for w in result["warnings"]), result["warnings"]


def test_m6_invalid_cards_rejected(knowledge):
    base = {
        "category": "formwork_support", "slab_thickness_m": 0.12, "story_height_m": 3.9,
        "step_m": 1.5, "pole_spacing_m": [1.0, 1.0], "pipe_spec": "48.3x3.6",
        "wind": "不组合",
        "loads": {"g1k_kN_per_m2": 0.75, "concrete_kN_per_m3": 24.0,
                  "rebar_kN_per_m3_slab": 1.1, "q1k_kN_per_m2": 1.0},
    }
    for mutate in (
        lambda c: c.update(category="coupler_steel_pipe_scaffold"),
        lambda c: c.update(pole_spacing_m=[0, 1.0]),
        lambda c: c.update(slab_thickness_m=0),
        lambda c: c["loads"].update(concrete_kN_per_m3=0),
        lambda c: c.pop("step_m"),
    ):
        card = copy.deepcopy(base)
        mutate(card)
        with pytest.raises(CardError):
            run_calc("M-6", card, knowledge)


def test_m5_without_nk_or_geometry_rejected(knowledge):
    card = {
        "category": "coupler_steel_pipe_scaffold", "pipe_spec": "48.3x3.6",
        "foundation": {"type": "回填土", "fgk_kPa": 180.0, "reduction": 0.4,
                       "pad_m": [0.4, 0.2]},
    }
    with pytest.raises(CardError):
        run_calc("M-5", card, knowledge)


# ---- 参数扫描回归（单调性与边界）----

def _ratio_m1(card, knowledge):
    result = run_calc("M-1", card, knowledge)
    assert result["status"] == "ok", result["status_note"]
    return result["checks"][0]["ratio"]


def test_sweep_build_height_monotonic(knowledge):
    """H↑ → 轴力↑ → 应力比↑（严格单调）。"""
    ratios = []
    for h_build in (6.0, 9.0, 12.0, 15.0, 18.0, 21.0, 24.0):
        card = copy.deepcopy(BASE_M1)
        card["build_height_m"] = h_build
        ratios.append(_ratio_m1(card, knowledge))
    assert ratios == sorted(ratios), ratios
    assert len(set(ratios)) == len(ratios)


def test_sweep_live_load_monotonic(knowledge):
    card = copy.deepcopy(BASE_M1)
    ratios = []
    for live in (2.0, 2.5, 3.0, 3.5):
        card["loads"]["live_kN_per_m2"] = live
        ratios.append(_ratio_m1(card, knowledge))
    assert ratios == sorted(ratios)


def test_sweep_step_monotonic_over_gk_table(knowledge):
    """步距↑（表A.0.1 域内）→ λ↑ → φ↓ 主导，应力比↑。"""
    ratios = []
    for step in (1.2, 1.35, 1.5, 1.8, 2.0):
        card = copy.deepcopy(BASE_M1)
        card["step_m"] = step
        ratios.append(_ratio_m1(card, knowledge))
    assert ratios == sorted(ratios), ratios


def test_sweep_cross_spacing_via_mu(knowledge):
    """立杆横距 lb 沿表5.2.8 档位↑ → μ↑ → λ↑ → 应力比↑。"""
    ratios = []
    for lb in (1.05, 1.30, 1.55):
        card = copy.deepcopy(BASE_M1)
        card["cross_spacing_m"] = lb
        card["wall_tie"] = "three_step_three_span"
        ratios.append(_ratio_m1(card, knowledge))
    assert ratios == sorted(ratios), ratios


def test_sweep_board_layers_monotonic(knowledge):
    card = copy.deepcopy(BASE_M1)
    ratios = []
    for layers in (0, 1, 2, 3, 4):
        card["loads"]["board_layers"] = layers
        ratios.append(_ratio_m1(card, knowledge))
    assert ratios == sorted(ratios)


def test_sweep_m2_wind_monotonic(knowledge):
    """风压↑ → 组合风应力比↑（M-2）。"""
    card = copy.deepcopy(BASE_M1)
    card["wind"] = {"w0_kN_per_m2": 0.4, "mu_z": 1.0,
                    "scaffold_state": "enclosed_net", "shape_phi": 0.8,
                    "back_wall": "全封闭墙"}
    ratios = []
    for w0 in (0.2, 0.3, 0.4, 0.5):
        card["wind"]["w0_kN_per_m2"] = w0
        result = run_calc("M-2", card, knowledge)
        assert result["status"] == "ok"
        ratios.append(result["checks"][0]["ratio"])
    assert ratios == sorted(ratios)


def test_sweep_m4_wind_antislip_boundary(knowledge):
    """M-4 风压扫描锁定抗滑比值单调，且大风压下越过 1.0（fail 路径再现）。"""
    base_card = {
        "category": "coupler_steel_pipe_scaffold", "rows": "double",
        "build_height_m": 12.0, "step_m": 1.8, "long_spacing_m": 1.5,
        "wall_tie": "two_step_three_span", "tie_type": "steel_pipe_coupler",
        "tie_length_m": 1.35, "pipe_spec": "48.3x3.6",
        "wind": {"wk_kN_per_m2": 0.10},
    }
    ratios = []
    for wk in (0.05, 0.10, 0.20, 0.32, 0.40):
        card = copy.deepcopy(base_card)
        card["wind"]["wk_kN_per_m2"] = wk
        result = run_calc("M-4", card, knowledge)
        assert result["status"] == "ok"
        antislip = [c for c in result["checks"] if c["item"] == "antislip"][0]
        ratios.append(antislip["ratio"])
    assert ratios == sorted(ratios), ratios
    assert ratios[0] < 1.0 < ratios[-1]


def test_sweep_m5_pad_area_inverse(knowledge):
    """垫板面积↑ → 基底压力↓（反比）。"""
    base_card = {
        "category": "coupler_steel_pipe_scaffold", "pipe_spec": "48.3x3.6",
        "foundation": {"type": "回填土", "fgk_kPa": 180.0, "reduction": 0.4,
                       "pad_m": [0.4, 0.2], "nk_kN": 4.2615},
    }
    ratios = []
    for pad in ([0.4, 0.2], [0.5, 0.3], [0.6, 0.4]):
        card = copy.deepcopy(base_card)
        card["foundation"]["pad_m"] = pad
        result = run_calc("M-5", card, knowledge)
        ratios.append(result["checks"][0]["ratio"])
    assert ratios == sorted(ratios, reverse=True), ratios


def test_sweep_m6_slab_thickness_monotonic(knowledge):
    """板厚↑ → 混凝土/钢筋自重↑ → 立柱应力比↑。"""
    base_card = {
        "category": "formwork_support", "story_height_m": 3.9,
        "step_m": 1.5, "pole_spacing_m": [1.0, 1.0], "pipe_spec": "48.3x3.6",
        "wind": "不组合",
        "loads": {"g1k_kN_per_m2": 0.75, "concrete_kN_per_m3": 24.0,
                  "rebar_kN_per_m3_slab": 1.1, "q1k_kN_per_m2": 1.0},
    }
    ratios = []
    for slab in (0.08, 0.10, 0.12, 0.15, 0.18):
        card = copy.deepcopy(base_card)
        card["slab_thickness_m"] = slab
        result = run_calc("M-6", card, knowledge)
        assert result["status"] == "ok"
        ratios.append(result["checks"][0]["ratio"])
    assert ratios == sorted(ratios), ratios


def test_lambda_boundary_250_to_formula(knowledge):
    """λ 边界：250 档查表 0.117；恰过 250 走 7320/λ² 公式，比值连续无跳变。"""
    from scaffold_formwork_checker.engine import tables
    phi_250 = tables.phi_of(250.0)
    phi_251 = tables.phi_of(251.0)
    assert phi_250 == 0.117
    assert abs(phi_251 - 7320.0 / (251.0 ** 2)) < 1e-15
    assert abs(phi_250 - phi_251) < 0.002  # 边界连续性（表注公式与表档衔接）
