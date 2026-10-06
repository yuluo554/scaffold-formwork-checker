# -*- coding: utf-8 -*-
"""算例真值库守门（M1 DoD：≥10 例、来源登记、真值自洽）。"""

import json
import math
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES_DIR = os.path.join(REPO_ROOT, "data", "examples")


def _examples():
    names = sorted(n for n in os.listdir(EXAMPLES_DIR) if n.endswith(".json"))
    out = []
    for name in names:
        with open(os.path.join(EXAMPLES_DIR, name), encoding="utf-8") as f:
            out.append(json.load(f))
    return out


def test_at_least_ten_examples_with_source():
    exs = _examples()
    assert len(exs) >= 10
    for ex in exs:
        src = ex["source"]
        assert src.get("type"), ex["example_id"]
        assert src.get("standard"), ex["example_id"]
        assert src.get("recalc_tool"), ex["example_id"]
        assert ex["input_card"], ex["example_id"]
        assert ex["expect"]["checks"], ex["example_id"]


def test_module_coverage():
    exs = _examples()
    modules = {ex["module"] for ex in exs}
    assert {"M-1", "M-2", "M-3", "M-4", "M-5", "M-6"} <= modules, modules


def test_verdict_consistent_with_ratio():
    for ex in _examples():
        for c in ex["expect"]["checks"]:
            expect = "pass" if c["ratio"] <= 1.0 else "fail"
            assert c["verdict"] == expect, (ex["example_id"], c)
            assert c["tolerance"] > 0


def test_fail_path_examples_exist():
    exs = _examples()
    fails = [ex for ex in exs if any(c["verdict"] == "fail" for c in ex["expect"]["checks"])]
    assert len(fails) >= 1, "真值库须含不合格路径（防引擎恒 pass 伪装正确）"


def test_intermediate_self_consistency():
    """中间量算术自洽：σ=N/(φA)（或加 Mw/W）按例内字段复算一致。"""
    for ex in _examples():
        it = ex["expect"].get("intermediate") or {}
        if ex["module"] in ("M-1", "M-2") and "phi" in it:
            sigma = it["N_design_kN"] * 1000.0 / (it["phi"] * 506.0)
            if "Mw_kNm" in it:
                sigma += it["Mw_kNm"] * 1e6 / 5260.0
            assert abs(sigma - it["sigma_N_per_mm2"]) < 0.01, ex["example_id"]
        if ex["module"] == "M-6" and "phi" in it:
            n = it.get("N_design_kN") or it.get("Nw_kN")
            sigma = n * 1000.0 / (it["phi"] * 506.0)
            if "Mw_kNm" in it:
                sigma += it["Mw_kNm"] * 1e6 / 5260.0
            assert abs(sigma - it["sigma_N_per_mm2"]) < 0.01, ex["example_id"]
        if ex["module"] == "M-5" or "p_kPa" in it:
            if "Nk_kN" in it:
                assert abs(it["Nk_kN"] / it["A_m2"] - it["pk_kPa"]) < 0.01, ex["example_id"]
            if "N_kN" in it:
                assert abs(it["N_kN"] / it["A_m2"] - it["p_kPa"]) < 0.01, ex["example_id"]
        if "lambda" in it and "phi" in it:
            assert 0 < it["phi"] < 1.0
            assert 0 < it["lambda"] <= 250


def test_lambda_ceil_lookup_convention():
    """查表口径：λ=ceil(l0/i)，档位值与本库锚点一致（引擎同口径）。"""
    anchors = {85: 0.692, 95: 0.626, 191: 0.197, 197: 0.186, 236: 0.131}
    for ex in _examples():
        it = ex["expect"].get("intermediate") or {}
        lam = it.get("lambda")
        if lam is None:
            continue
        key = int(math.ceil(lam))
        if key in anchors:
            assert it["phi"] == anchors[key], (ex["example_id"], key, it["phi"])
