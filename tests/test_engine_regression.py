# -*- coding: utf-8 -*-
"""M2 算例真值回归：13 例逐例过引擎，checks（容差内）+ 中间量比对 + 模块自动识别。

这是 M2 DoD ①（算例真值通过率 100%）的守门测试。
"""

import glob
import json
import math
import os

import pytest

from scaffold_formwork_checker.engine import detect_module, load_knowledge, run_calc

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES_DIR = os.path.join(REPO_ROOT, "data", "examples")

INTERMEDIATE_TOL = 0.02  # 真值按 4 位小数落盘，0.02 覆盖舍入与浮点噪声


@pytest.fixture(scope="module")
def knowledge():
    return load_knowledge(os.path.join(REPO_ROOT, "data"))


def _examples():
    out = []
    for path in sorted(glob.glob(os.path.join(EXAMPLES_DIR, "*.json"))):
        with open(path, encoding="utf-8") as f:
            out.append(json.load(f))
    return out


def test_thirteen_examples_loaded():
    assert len(_examples()) == 13


@pytest.mark.parametrize("example", _examples(), ids=lambda e: e["example_id"])
def test_example_matches_truth(example, knowledge):
    card = example["input_card"]
    # 模块自动识别与真值库登记一致
    assert detect_module(card) == example["module"], example["example_id"]
    result = run_calc(example["module"], card, knowledge)
    assert result["status"] == "ok", (example["example_id"], result["status_note"])
    # ① 期望检查项逐项比对（item 定位；ratio 容差内；verdict 相等）
    for exp_check in example["expect"]["checks"]:
        matched = [c for c in result["checks"] if c["item"] == exp_check["item"]]
        assert matched, (example["example_id"], exp_check["item"], list(result["checks"]))
        got = matched[0]
        assert abs(got["ratio"] - exp_check["ratio"]) <= exp_check["tolerance"], (
            example["example_id"], exp_check["item"], got["ratio"], exp_check["ratio"])
        assert got["verdict"] == exp_check["verdict"], (
            example["example_id"], exp_check["item"], got["verdict"], exp_check["verdict"])
        assert got["clause_refs"], (example["example_id"], exp_check["item"])
    # ② 中间量逐项比对（键名与真值库对齐）
    for key, expect_v in (example["expect"].get("intermediate") or {}).items():
        assert key in result["detail"], (example["example_id"], key)
        got_v = result["detail"][key]
        if isinstance(expect_v, (int, float)):
            assert abs(got_v - expect_v) <= INTERMEDIATE_TOL, (
                example["example_id"], key, got_v, expect_v)


def test_phi_values_pinned_by_examples(knowledge):
    """φ 锚点经算例再锁：各例引擎 φ 与真值库 φ 完全相等。"""
    anchors = {85: 0.692, 95: 0.626, 191: 0.197, 197: 0.186, 236: 0.131}
    for example in _examples():
        detail = example["expect"].get("intermediate") or {}
        lam = detail.get("lambda")
        if lam is None or int(math.ceil(lam)) not in anchors:
            continue
        result = run_calc(example["module"], example["input_card"], knowledge)
        assert result["detail"]["phi"] == anchors[int(math.ceil(lam))], example["example_id"]


def test_gk_table_lookup_equivalence(knowledge):
    """nw-001 卡去掉显式 gk 后由表A.0.1 查取，结果不变（查表路径回归）。"""
    example = [e for e in _examples() if e["example_id"] == "EX-lizhigan-nw-001"][0]
    base = run_calc("M-1", example["input_card"], knowledge)
    card_wo_gk = json.loads(json.dumps(example["input_card"]))
    del card_wo_gk["loads"]["gk_struct_kN_per_m"]
    via_table = run_calc("M-1", card_wo_gk, knowledge)
    assert base["status"] == via_table["status"] == "ok"
    assert via_table["detail"]["gk_kN_per_m"] == pytest.approx(0.1295, abs=1e-9)
    assert via_table["detail"]["N_design_kN"] == pytest.approx(base["detail"]["N_design_kN"], abs=1e-9)
    assert via_table["checks"][0]["ratio"] == pytest.approx(base["checks"][0]["ratio"], abs=1e-9)


def test_fail_path_examples_fail_via_engine(knowledge):
    """不合格路径例经引擎仍判 fail（防引擎恒 pass 伪装正确）。"""
    fails = [e for e in _examples()
             if any(c["verdict"] == "fail" for c in e["expect"]["checks"])]
    assert len(fails) >= 2
    for example in fails:
        result = run_calc(example["module"], example["input_card"], knowledge)
        got_fail = [c for c in result["checks"] if c["verdict"] == "fail"]
        assert got_fail, (example["example_id"], result["checks"])
