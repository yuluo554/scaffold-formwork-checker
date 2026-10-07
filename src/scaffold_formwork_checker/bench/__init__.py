# -*- coding: utf-8 -*-
"""内置基准（M4 正式化）：三套件一条命令跑完（sfc bench）。

- examples 套件：算例真值库逐例过引擎，容差对账（examples_suite.py）；
- synthetic 套件：冻结 fixtures 跑"解析+核查"，按"全部非 pass 集合"对账
  （本模块，M3 dev 版评测器直接转正）；
- grading 套件：分级判定边界值用例表（grading_suite.py）。

达标门限 BENCH_TARGETS（README 基准表同源）：examples 通过率 100%、
synthetic F1≥0.95 且误报 0、grading 通过率 100%。全套零 API、离线、确定性。

synthetic 真值语义（M1 决策 #20）：main_expect + also_expect 构成期望的
非 pass 集合。评测器把管线输出中 verdict != "pass" 的 findings 与期望集合对账：

- 期望命中（rule_id 相同 + verdict 一致 + 数值字段容差内 + clause_ref 被包含）→ TP；
- 期望未命中 → FN（漏报：防"漏报伪装成正确"）；
- 输出多出的非 pass 项 → FP（误报）。
"""

import json
import os

from ..engine.loader import load_knowledge
from ..parse import parse_scheme
from ..rules import load_checks_table, run_checks
from .examples_suite import evaluate_example, load_examples, run_examples_suite
from .grading_suite import GRADING_CASES, run_grading_suite

_NUM_TOL = 1e-6

# 达标门限（sfc bench 退出码 0/1 的判定依据；指标同源写入 README 基准表）
BENCH_TARGETS = {
    "examples_pass_rate": 1.0,      # 算例真值回归通过率（13 例全对账）
    "synthetic_f1_min": 0.95,       # 合成基准 F1（M3 dev 版目标沿用）
    "synthetic_fp_max": 0,          # 合成基准误报数（干净对照 0 误报）
    "grading_pass_rate": 1.0,       # 分级边界值用例通过率
}


def _match(expected, finding):
    """期望项与输出 finding 对账：rule_id + verdict + 数值 + 条款号包含。"""
    if finding is None or finding.get("verdict") != expected.get("verdict"):
        return False
    for key in ("actual", "limit_value", "scheme_value", "calcbook_value"):
        if key in expected:
            got = finding.get(key)
            if got is None:
                return False
            if abs(float(got) - float(expected[key])) > _NUM_TOL:
                return False
    clause_ref = expected.get("clause_ref")
    if clause_ref and clause_ref not in (finding.get("clause_refs") or []):
        return False
    return True


def evaluate_fixture(docx_path, truth_path, knowledge=None, checks_table=None):
    """单 fixture 评测：解析+核查 → 与真值非 pass 集合对账。"""
    with open(truth_path, encoding="utf-8") as f:
        truth = json.load(f)
    if knowledge is None:
        knowledge = load_knowledge()
    if checks_table is None:
        checks_table = load_checks_table()
    parsed = parse_scheme(docx_path)
    report = run_checks(parsed.scheme_card, parsed.calcbook_card, knowledge,
                        checks_table)
    out = {}
    for finding in report["findings"]:
        if finding["verdict"] != "pass":
            out[finding["rule_id"]] = finding
    expected = list(truth.get("main_expect") or []) + list(truth.get("also_expect") or [])
    tp = 0
    misses = []
    for e in expected:
        if _match(e, out.get(e.get("rule_id"))):
            tp += 1
        else:
            misses.append(e)
    fn = len(expected) - tp
    expected_ids = {e.get("rule_id") for e in expected}
    fps = sorted(rid for rid in out if rid not in expected_ids)
    return {
        "fixture_id": truth.get("fixture_id"),
        "injection": truth.get("injection"),
        "clean_baseline": bool(truth.get("clean_baseline")),
        "tp": tp,
        "fn": fn,
        "fp": fps,
        "misses": misses,
        "unknown_slots": list(parsed.scheme_card.unknown_slots),
    }


def run_synthetic_suite(synthetic_dir=None, data_dir=None):
    """synthetic 套件：读 manifest 逐 fixture 评测，汇总检出率/误报/F1。"""
    if synthetic_dir is None:
        base = load_knowledge(data_dir).data_dir
        synthetic_dir = os.path.join(base, "synthetic")
    manifest_path = os.path.join(synthetic_dir, "manifest.json")
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    knowledge = load_knowledge(data_dir)
    checks_table = load_checks_table()
    per_fixture = []
    for fx in manifest["fixtures"]:
        per_fixture.append(evaluate_fixture(
            os.path.join(synthetic_dir, fx["docx"]),
            os.path.join(synthetic_dir, fx["truth"]),
            knowledge=knowledge, checks_table=checks_table))
    tp = sum(x["tp"] for x in per_fixture)
    fn = sum(x["fn"] for x in per_fixture)
    fp = sum(len(x["fp"]) for x in per_fixture)
    clean = [x for x in per_fixture if x["clean_baseline"]]
    clean_fp = sum(len(x["fp"]) for x in clean)
    by_injection = {}
    for x in per_fixture:
        bucket = by_injection.setdefault(
            x["injection"], {"tp": 0, "fn": 0, "fp": 0, "fixtures": 0})
        bucket["tp"] += x["tp"]
        bucket["fn"] += x["fn"]
        bucket["fp"] += len(x["fp"])
        bucket["fixtures"] += 1
    for bucket in by_injection.values():
        detected = bucket["tp"] + bucket["fn"]
        bucket["detection_rate"] = (bucket["tp"] / detected) if detected else 1.0
    precision = (tp / (tp + fp)) if (tp + fp) else 1.0
    recall = (tp / (tp + fn)) if (tp + fn) else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "fixtures": len(per_fixture),
        "per_fixture": per_fixture,
        "by_injection": by_injection,
        "metrics": {
            "expected_non_pass": tp + fn,
            "tp": tp,
            "fn": fn,
            "fp": fp,
            "detection_rate": recall,
            "false_positive_count": fp,
            "false_positive_rate": (fp / (tp + fp)) if (tp + fp) else 0.0,
            "clean_baseline_count": len(clean),
            "clean_baseline_fp": clean_fp,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        },
    }


def _targets_met(examples, synthetic, grading):
    """逐门限求值：返回 {门限名: bool}（README 基准表同源口径）。"""
    m = synthetic["metrics"]
    return {
        "examples_pass_rate": examples["pass_rate"] >= BENCH_TARGETS["examples_pass_rate"],
        "synthetic_f1": m["f1"] >= BENCH_TARGETS["synthetic_f1_min"],
        "synthetic_false_positives": (m["false_positive_count"]
                                      <= BENCH_TARGETS["synthetic_fp_max"]),
        "grading_pass_rate": grading["pass_rate"] >= BENCH_TARGETS["grading_pass_rate"],
    }


def run_all(data_dir=None):
    """三套件一条命令跑完：examples + synthetic + grading → 汇总与达标判定。"""
    examples = run_examples_suite(data_dir)
    synthetic = run_synthetic_suite(None, data_dir)
    grading = run_grading_suite(data_dir)
    targets = _targets_met(examples, synthetic, grading)
    return {
        "suites": {
            "examples": {
                "examples": examples["examples"],
                "passed": examples["passed"],
                "pass_rate": examples["pass_rate"],
                "fail_examples": examples["fail_examples"],
            },
            "synthetic": {"metrics": synthetic["metrics"],
                          "by_injection": synthetic["by_injection"]},
            "grading": {
                "cases": grading["cases"],
                "passed": grading["passed"],
                "pass_rate": grading["pass_rate"],
                "fail_cases": grading["fail_cases"],
            },
        },
        "targets": targets,
        "all_pass": all(targets.values()),
    }


__all__ = [
    "BENCH_TARGETS", "GRADING_CASES", "evaluate_example", "evaluate_fixture",
    "load_examples", "run_all", "run_examples_suite", "run_grading_suite",
    "run_synthetic_suite",
]
