# -*- coding: utf-8 -*-
"""M2 条文纪律守门：待核对硬拦截（M2 DoD ③）。

任一依赖条目 status=待核对 → 模块整体返回"不可验算（依据未核对）"，不带任何计算结果。
用临时数据目录变异 formulas/thresholds 状态驱动（仓库数据本体由 test_clause_library 锁定）。
"""

import json
import os
import shutil

import pytest

from scaffold_formwork_checker.engine import Knowledge, KnowledgeError, load_knowledge, run_calc
from scaffold_formwork_checker.engine import scalars

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAUSES_DIR = os.path.join(REPO_ROOT, "data", "knowledge", "clauses")

CARDS = {
    "M-1": {
        "category": "coupler_steel_pipe_scaffold", "rows": "double",
        "build_height_m": 12.0, "step_m": 1.8, "long_spacing_m": 1.5,
        "cross_spacing_m": 1.05, "wall_tie": "two_step_three_span",
        "pipe_spec": "48.3x3.6", "steel_grade": "Q235A", "wind": "不组合",
        "loads": {"gk_struct_kN_per_m": 0.1295, "board_kN_per_m2": 0.3,
                  "board_layers": 2, "rail_kN_per_m": 0.16,
                  "safety_net_kN_per_m2": 0.01, "live_kN_per_m2": 2.0},
    },
    "M-3": {
        "category": "coupler_steel_pipe_scaffold", "rows": "double", "member": "cross",
        "step_m": 1.8, "long_spacing_m": 1.5, "cross_spacing_m": 1.05,
        "pipe_spec": "48.3x3.6",
        "loads": {"board_kN_per_m2": 0.3, "live_kN_per_m2": 2.0},
    },
    "M-4": {
        "category": "coupler_steel_pipe_scaffold", "rows": "double",
        "build_height_m": 12.0, "step_m": 1.8, "long_spacing_m": 1.5,
        "wall_tie": "two_step_three_span", "tie_type": "steel_pipe_coupler",
        "tie_length_m": 1.35, "pipe_spec": "48.3x3.6",
        "wind": {"wk_kN_per_m2": 0.10},
    },
    "M-5": {
        "category": "coupler_steel_pipe_scaffold", "pipe_spec": "48.3x3.6",
        "foundation": {"type": "回填土", "fgk_kPa": 180.0, "reduction": 0.4,
                       "pad_m": [0.4, 0.2], "nk_kN": 4.2615},
    },
    "M-6": {
        "category": "formwork_support", "slab_thickness_m": 0.12, "story_height_m": 3.9,
        "step_m": 1.5, "pole_spacing_m": [1.0, 1.0], "pipe_spec": "48.3x3.6",
        "wind": "不组合",
        "loads": {"g1k_kN_per_m2": 0.75, "concrete_kN_per_m3": 24.0,
                  "rebar_kN_per_m3_slab": 1.1, "q1k_kN_per_m2": 1.0},
    },
}
# M-2 / M-4 与 M-1 同族，仅在用例内派生


@pytest.fixture()
def mutated_data_dir(tmp_path):
    """复制条款库到临时目录，供用例变异 status。"""
    dst = tmp_path / "knowledge" / "clauses"
    dst.parent.mkdir()
    shutil.copytree(CLAUSES_DIR, str(dst))
    return tmp_path


def _flip_status(data_dir, filename, entry_id, status="待核对"):
    entry_key = "formulas" if filename == "formulas.json" else "thresholds"
    path = os.path.join(str(data_dir), "knowledge", "clauses", filename)
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    id_field = entry_key[:-1] + "_id"
    for x in doc[entry_key]:
        if x[id_field] == entry_id:
            x["status"] = status
            break
    else:
        raise AssertionError(entry_id)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")


def test_repo_modules_currently_unblocked():
    """仓库数据现状：6 模块依赖面全部已核对（若新增待核对依赖须显式走拦截路径）。"""
    kn = load_knowledge(os.path.join(REPO_ROOT, "data"))
    for module_id in ("M-1", "M-2", "M-3", "M-4", "M-5", "M-6"):
        assert kn.unverified(module_id) == [], module_id


@pytest.mark.parametrize("filename,entry_id,module_id", [
    ("formulas.json", "F-J130-stab-nw", "M-1"),
    ("thresholds.json", "T-JGJ130-mu-coef", "M-1"),
    ("formulas.json", "F-J130-Mw", "M-2"),
    ("thresholds.json", "T-JGJ130-section-props", "M-2"),
    ("formulas.json", "F-J130-beam-deflection", "M-3"),
    ("thresholds.json", "T-JGJ130-tie-N0", "M-4"),
    ("thresholds.json", "T-JGJ130-fg-reduction", "M-5"),
    ("formulas.json", "F-J162-column", "M-6"),
])
def test_pending_blocks_module(mutated_data_dir, filename, entry_id, module_id):
    _flip_status(mutated_data_dir, filename, entry_id)
    kn = Knowledge(str(mutated_data_dir))
    assert entry_id in kn.unverified(module_id), (module_id, entry_id)
    if module_id == "M-2":
        card = dict(CARDS["M-1"], wind={
            "w0_kN_per_m2": 0.4, "mu_z": 1.0, "scaffold_state": "enclosed_net",
            "shape_phi": 0.8, "back_wall": "全封闭墙"})
    else:
        card = CARDS[module_id]
    result = run_calc(module_id, card, kn)
    assert result["status"] == "blocked", (module_id, result["status"], result["status_note"])
    assert result["checks"] == []
    assert "依据未核对" in result["status_note"]
    assert entry_id in result["status_note"]


def test_second_layer_threshold_access_blocked(mutated_data_dir):
    """第二层拦截：即使模块级放行，取用待核对阈值也直接抛错。"""
    _flip_status(mutated_data_dir, "thresholds.json", "T-JGJ130-steel-design")
    kn = Knowledge(str(mutated_data_dir))
    with pytest.raises(KnowledgeError) as exc:
        scalars.steel_f_130(kn)
    assert "不得进入计算路径" in str(exc.value)


def test_blocked_carries_no_numbers(mutated_data_dir):
    """拦截结果不含任何数值（防"带病计算"从旁路漏出）。"""
    _flip_status(mutated_data_dir, "formulas.json", "F-J130-N-nw")
    kn = Knowledge(str(mutated_data_dir))
    result = run_calc("M-1", CARDS["M-1"], kn)
    assert result["status"] == "blocked"
    assert result["detail"] == {}
    assert result["warnings"] == []
