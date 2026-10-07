# -*- coding: utf-8 -*-
"""bench examples 套件：算例真值库逐例过引擎（M2 回归口径的正式化）。

与 tests/test_engine_regression.py 同口径：
- detect_module 自动识别与真值库登记模块一致；
- expect.checks 逐项：item 定位、ratio 容差内、verdict 相等、条款号非空；
- expect.intermediate 逐键比对（容差 0.02，真值按 4 位小数落盘）。

指标：通过率（目标 100%）。全套零 API、离线、确定性。
"""

import glob
import json
import os

from ..engine import detect_module, run_calc
from ..engine.loader import KnowledgeError, find_data_dir, load_knowledge

INTERMEDIATE_TOL = 0.02


def _resolve_base(data_dir):
    base = find_data_dir(data_dir)
    if base is None:
        raise KnowledgeError(
            "未找到数据目录（含 knowledge/clauses）：可用 --data-dir 指定或设 SFC_DATA")
    return base


def _examples_dir(data_dir):
    base = _resolve_base(data_dir)
    return base, os.path.join(base, "examples")


def load_examples(data_dir=None):
    """读入算例真值库（data/examples/*.json，按文件名排序）。"""
    _, examples_dir = _examples_dir(data_dir)
    out = []
    for path in sorted(glob.glob(os.path.join(examples_dir, "*.json"))):
        with open(path, encoding="utf-8") as f:
            out.append(json.load(f))
    if not out:
        raise KnowledgeError("算例真值库为空：%s" % examples_dir)
    return out


def evaluate_example(example, knowledge):
    """单算例评测：模块识别 + 引擎复算 + checks/中间量对账。

    返回 {"example_id","module","ok","failures":[原因串]}；ok=全部对账通过。
    """
    failures = []
    card = example["input_card"]
    try:
        detected = detect_module(card)
    except Exception as exc:  # CardError 等：该例无法识别即记失败，不中断整套
        return {"example_id": example["example_id"], "module": example["module"],
                "ok": False, "failures": ["模块识别失败：%s" % exc]}
    if detected != example["module"]:
        failures.append("模块识别 %s != 登记模块 %s" % (detected, example["module"]))
        return {"example_id": example["example_id"], "module": example["module"],
                "ok": False, "failures": failures}
    try:
        result = run_calc(example["module"], card, knowledge)
    except Exception as exc:
        failures.append("引擎运行异常：%s" % exc)
        return {"example_id": example["example_id"], "module": example["module"],
                "ok": False, "failures": failures}
    if result.get("status") != "ok":
        failures.append("status=%s（%s）" % (result.get("status"),
                                            result.get("status_note", "")))
        return {"example_id": example["example_id"], "module": example["module"],
                "ok": False, "failures": failures}
    got_by_item = {c["item"]: c for c in result["checks"]}
    for exp_check in example["expect"]["checks"]:
        got = got_by_item.get(exp_check["item"])
        if got is None:
            failures.append("缺检查项 %s" % exp_check["item"])
            continue
        if abs(got["ratio"] - exp_check["ratio"]) > exp_check["tolerance"]:
            failures.append("%s ratio %.6f 超出真值 %.6f±%s"
                            % (exp_check["item"], got["ratio"],
                               exp_check["ratio"], exp_check["tolerance"]))
        if got["verdict"] != exp_check["verdict"]:
            failures.append("%s verdict %s != 真值 %s"
                            % (exp_check["item"], got["verdict"],
                               exp_check["verdict"]))
        if not got.get("clause_refs"):
            failures.append("%s 缺条款号" % exp_check["item"])
    for key, expect_v in (example["expect"].get("intermediate") or {}).items():
        if key not in result["detail"]:
            failures.append("缺中间量 %s" % key)
            continue
        got_v = result["detail"][key]
        if isinstance(expect_v, (int, float)) and abs(got_v - expect_v) > INTERMEDIATE_TOL:
            failures.append("中间量 %s %.6f != 真值 %.6f（容差 %s）"
                            % (key, got_v, expect_v, INTERMEDIATE_TOL))
    return {"example_id": example["example_id"], "module": example["module"],
            "ok": not failures, "failures": failures}


def run_examples_suite(data_dir=None):
    """examples 套件：逐例评测并汇总通过率。"""
    base = _resolve_base(data_dir)
    knowledge = load_knowledge(base)
    per_example = [evaluate_example(ex, knowledge)
                   for ex in load_examples(base)]
    passed = sum(1 for x in per_example if x["ok"])
    n = len(per_example)
    return {
        "examples": n,
        "passed": passed,
        "pass_rate": (passed / n) if n else 0.0,
        "fail_examples": [x["example_id"] for x in per_example if not x["ok"]],
        "per_example": per_example,
    }


__all__ = ["evaluate_example", "load_examples", "run_examples_suite",
           "INTERMEDIATE_TOL"]
