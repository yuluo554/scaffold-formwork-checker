# -*- coding: utf-8 -*-
"""sfc calc 端到端：参数卡文件 → 结果 JSON；退出码 0/1/2 语义（口径锁定）。"""

import json
import os
import shutil

import pytest

from scaffold_formwork_checker.cli import EXIT_DEGRADED, EXIT_INPUT_ERROR, EXIT_OK, main

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES_DIR = os.path.join(REPO_ROOT, "data", "examples")
CLAUSES_DIR = os.path.join(REPO_ROOT, "data", "knowledge", "clauses")

NW_CARD = {
    "category": "coupler_steel_pipe_scaffold", "rows": "double",
    "build_height_m": 12.0, "step_m": 1.8, "long_spacing_m": 1.5,
    "cross_spacing_m": 1.05, "wall_tie": "two_step_three_span",
    "pipe_spec": "48.3x3.6", "steel_grade": "Q235A", "wind": "不组合",
    "loads": {"gk_struct_kN_per_m": 0.1295, "board_kN_per_m2": 0.3,
              "board_layers": 2, "rail_kN_per_m": 0.16,
              "safety_net_kN_per_m2": 0.01, "live_kN_per_m2": 2.0},
}


def _write_card(tmp_path, card, name="card.json"):
    path = os.path.join(str(tmp_path), name)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(card, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path


def test_calc_ok_exit_0(capsys, tmp_path):
    path = _write_card(tmp_path, NW_CARD)
    assert main(["calc", path]) == EXIT_OK
    result = json.loads(capsys.readouterr().out)
    assert result["module_id"] == "M-1"
    assert result["status"] == "ok"
    check = result["checks"][0]
    assert check["item"] == "lizhigan_stability"
    assert check["verdict"] == "pass"
    assert abs(check["ratio"] - 0.2814) <= 0.01
    assert "JGJ130-5.2.6" in check["clause_refs"]


def test_calc_example_cards_auto_detect(capsys, tmp_path):
    """13 例真值卡逐张过 CLI：自动识别模块 + exit 0。"""
    for name in sorted(os.listdir(EXAMPLES_DIR)):
        if not name.endswith(".json"):
            continue
        src = os.path.join(EXAMPLES_DIR, name)
        with open(src, encoding="utf-8") as f:
            example = json.load(f)
        path = _write_card(tmp_path, example["input_card"], name)
        assert main(["calc", path]) == EXIT_OK, name
        result = json.loads(capsys.readouterr().out)
        assert result["module_id"] == example["module"], name
        for exp_check in example["expect"]["checks"]:
            got = [c for c in result["checks"] if c["item"] == exp_check["item"]][0]
            assert abs(got["ratio"] - exp_check["ratio"]) <= exp_check["tolerance"], name
            assert got["verdict"] == exp_check["verdict"], name


def test_calc_explicit_module_flag(capsys, tmp_path):
    path = _write_card(tmp_path, NW_CARD)
    assert main(["calc", path, "--module", "M-1"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["module_id"] == "M-1"


def test_calc_missing_file_exit_2(capsys, tmp_path):
    missing = os.path.join(str(tmp_path), "nope.json")
    assert main(["calc", missing]) == EXIT_INPUT_ERROR
    assert "不存在" in capsys.readouterr().err


def test_calc_bad_json_exit_2(capsys, tmp_path):
    path = os.path.join(str(tmp_path), "broken.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("{ not json")
    assert main(["calc", path]) == EXIT_INPUT_ERROR
    assert "解析失败" in capsys.readouterr().err


def test_calc_invalid_card_exit_2(capsys, tmp_path):
    card = dict(NW_CARD, step_m=0)
    path = _write_card(tmp_path, card)
    assert main(["calc", path]) == EXIT_INPUT_ERROR
    assert "参数错误" in capsys.readouterr().err


def test_calc_unknown_module_exit_2(capsys, tmp_path):
    path = _write_card(tmp_path, NW_CARD)
    assert main(["calc", path, "--module", "M-9"]) == EXIT_INPUT_ERROR


def test_calc_undetectable_card_exit_2(capsys, tmp_path):
    path = _write_card(tmp_path, {"category": "mystery"})
    assert main(["calc", path]) == EXIT_INPUT_ERROR
    assert "无法识别" in capsys.readouterr().err


def test_calc_blocked_exit_1(capsys, tmp_path):
    """待核对拦截 → exit 1（降级完成：结果可用但为拦截说明）。"""
    data_dir = os.path.join(str(tmp_path), "data")
    os.makedirs(os.path.join(data_dir, "knowledge"))
    shutil.copytree(CLAUSES_DIR, os.path.join(data_dir, "knowledge", "clauses"))
    fpath = os.path.join(data_dir, "knowledge", "clauses", "formulas.json")
    with open(fpath, encoding="utf-8") as f:
        doc = json.load(f)
    for x in doc["formulas"]:
        if x["formula_id"] == "F-J130-stab-nw":
            x["status"] = "待核对"
    with open(fpath, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    path = _write_card(tmp_path, NW_CARD)
    assert main(["calc", path, "--data-dir", data_dir]) == EXIT_DEGRADED
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["status"] == "blocked"
    assert "依据未核对" in result["status_note"]
    assert "依据未核对" in captured.err


def test_calc_missing_data_dir_exit_2(capsys, tmp_path):
    path = _write_card(tmp_path, NW_CARD)
    assert main(["calc", path, "--data-dir", os.path.join(str(tmp_path), "empty")]) == EXIT_INPUT_ERROR
    assert "条款库不可用" in capsys.readouterr().err
