# -*- coding: utf-8 -*-
"""M3 合成基准（dev 版）守门：M3 DoD ①。

口径：12 冻结 fixtures（5 类注入×2 + 干净对照×2）跑"解析+核查"，
按"全部非 pass 集合"对账（真值=main_expect+also_expect）：
- 检出率 100%、误报 0、F1≥0.95（dev 版目标全部达标）；
- 每类注入检出率 100%；干净对照 0 误报；
- 数值字段（actual/limit_value/scheme_value 等）与条款号严格对账。
"""

import os

from scaffold_formwork_checker.bench import evaluate_fixture, run_synthetic_suite

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
SYNTH_DIR = os.path.join(DATA_DIR, "synthetic")


def test_synthetic_suite_meets_dev_targets():
    suite = run_synthetic_suite(SYNTH_DIR, DATA_DIR)
    m = suite["metrics"]
    assert suite["fixtures"] == 12
    assert m["expected_non_pass"] == 14
    assert m["detection_rate"] == 1.0, m
    assert m["false_positive_count"] == 0, m
    assert m["false_positive_rate"] == 0.0
    assert m["f1"] >= 0.95
    assert m["clean_baseline_count"] == 2
    assert m["clean_baseline_fp"] == 0
    assert m["precision"] == 1.0 and m["recall"] == 1.0


def test_every_injection_category_fully_detected():
    suite = run_synthetic_suite(SYNTH_DIR, DATA_DIR)
    expected_categories = {"clean", "step_over", "walltie_over",
                           "brace_missing", "two_sheets", "grading_missing"}
    by = suite["by_injection"]
    assert set(by) == expected_categories
    for name, bucket in by.items():
        assert bucket["fixtures"] == 2, name
        assert bucket["fn"] == 0, name
        assert bucket["fp"] == 0, name
        assert bucket["detection_rate"] == 1.0, name


def test_clean_fixtures_have_zero_non_pass_findings():
    for fx in ("SY-clean-01", "SY-clean-02"):
        result = evaluate_fixture(
            os.path.join(SYNTH_DIR, fx + ".docx"),
            os.path.join(SYNTH_DIR, fx + ".truth.json"))
        assert result["tp"] == 0 and result["fn"] == 0 and result["fp"] == []
        assert result["unknown_slots"] == []


def test_defect_findings_carry_truth_numbers_and_clauses():
    """数值字段严格对账：step_over 的限值 1.8/2.0、walltie 的 3h 现算值。"""
    result = evaluate_fixture(
        os.path.join(SYNTH_DIR, "SY-step-over-01.docx"),
        os.path.join(SYNTH_DIR, "SY-step-over-01.truth.json"))
    assert result["tp"] == 2 and result["fn"] == 0 and result["fp"] == []
    result = evaluate_fixture(
        os.path.join(SYNTH_DIR, "SY-walltie-over-02.docx"),
        os.path.join(SYNTH_DIR, "SY-walltie-over-02.truth.json"))
    assert result["tp"] == 1 and result["fn"] == 0 and result["fp"] == []
    result = evaluate_fixture(
        os.path.join(SYNTH_DIR, "SY-grading-missing-02.docx"),
        os.path.join(SYNTH_DIR, "SY-grading-missing-02.truth.json"))
    assert result["tp"] == 2 and result["fn"] == 0 and result["fp"] == []
