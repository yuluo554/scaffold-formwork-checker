# -*- coding: utf-8 -*-
"""M4 bench 三套件守门（M4 DoD ①：基准零 API 可重复）。

口径：examples 13 例通过率 100%、synthetic 检出率 100%/误报 0/F1≥0.95、
grading 边界值用例通过率 100%；run_all 全部达标且两次运行结果一致
（确定性）。sfc bench 的指标即本模块口径（README 基准表同源）。
"""

import json
import os

from scaffold_formwork_checker.bench import (
    BENCH_TARGETS, GRADING_CASES, run_all, run_examples_suite,
    run_grading_suite, run_synthetic_suite,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")


def test_examples_suite_all_pass():
    suite = run_examples_suite(DATA_DIR)
    assert suite["examples"] == 13
    assert suite["passed"] == 13
    assert suite["pass_rate"] == 1.0
    assert suite["fail_examples"] == []


def test_grading_suite_all_pass():
    suite = run_grading_suite(DATA_DIR)
    # 用例表规模守门：落地 10 + 悬挑/附着/承重 9 + 模板支撑 14 + pending 2
    assert suite["cases"] == 35 == len(GRADING_CASES)
    assert suite["passed"] == 35
    assert suite["pass_rate"] == 1.0
    assert suite["fail_cases"] == []


def test_synthetic_suite_unchanged_from_m3():
    suite = run_synthetic_suite(os.path.join(DATA_DIR, "synthetic"), DATA_DIR)
    m = suite["metrics"]
    assert m["detection_rate"] == 1.0
    assert m["false_positive_count"] == 0
    assert m["f1"] >= BENCH_TARGETS["synthetic_f1_min"]
    assert m["clean_baseline_fp"] == 0


def test_run_all_targets_met():
    outcome = run_all(DATA_DIR)
    assert outcome["all_pass"] is True
    assert outcome["targets"] == {
        "examples_pass_rate": True,
        "synthetic_f1": True,
        "synthetic_false_positives": True,
        "grading_pass_rate": True,
    }
    assert outcome["suites"]["examples"]["pass_rate"] == 1.0
    assert outcome["suites"]["grading"]["pass_rate"] == 1.0


def test_run_all_is_deterministic():
    """两次运行 JSON 完全一致（可重复性，零时钟/零随机源）。"""
    first = json.dumps(run_all(DATA_DIR), ensure_ascii=False, sort_keys=True)
    second = json.dumps(run_all(DATA_DIR), ensure_ascii=False, sort_keys=True)
    assert first == second


def test_targets_thresholds_locked():
    assert BENCH_TARGETS == {
        "examples_pass_rate": 1.0,
        "synthetic_f1_min": 0.95,
        "synthetic_fp_max": 0,
        "grading_pass_rate": 1.0,
    }
