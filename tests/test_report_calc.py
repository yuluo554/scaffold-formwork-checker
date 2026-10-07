# -*- coding: utf-8 -*-
"""M4 报告守门：docx 验算书（M4 DoD ②③ + 报告内容纪律）。

- 位级一致：同输入两次生成字节完全相同（落盘 zip 规范化，全条目固定
  时间戳 + core/app.xml 覆写）；
- 0 外链：全部 .rels 条目无 TargetMode="External" 超链关系；
- 免责声明强制；blocked 结果不渲染计算数值。
"""

import json
import os

from report_helpers import assert_no_external_links, assert_no_timestamps, read_plain_text

from scaffold_formwork_checker.engine import load_knowledge, run_calc
from scaffold_formwork_checker.engine.result import blocked_result
from scaffold_formwork_checker.report import DISCLAIMER, generate_calc_report

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")


def _example_card():
    path = os.path.join(DATA_DIR, "examples", "EX-lizhigan-nw-001.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)["input_card"]


def _read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def test_calc_report_byte_identical_on_regeneration(tmp_path):
    knowledge = load_knowledge(DATA_DIR)
    card = _example_card()
    out1 = str(tmp_path / "a.docx")
    out2 = str(tmp_path / "b.docx")
    generate_calc_report(card, run_calc("M-1", card, knowledge), out1)
    generate_calc_report(card, run_calc("M-1", card, knowledge), out2)
    assert _read_bytes(out1) == _read_bytes(out2)


def test_calc_report_zero_external_links_and_no_timestamps(tmp_path):
    knowledge = load_knowledge(DATA_DIR)
    card = _example_card()
    out = str(tmp_path / "calc.docx")
    generate_calc_report(card, run_calc("M-1", card, knowledge), out)
    assert_no_external_links(out)
    assert_no_timestamps(out)


def test_calc_report_contains_sections_and_disclaimer(tmp_path):
    knowledge = load_knowledge(DATA_DIR)
    card = _example_card()
    out = str(tmp_path / "calc.docx")
    generate_calc_report(card, run_calc("M-1", card, knowledge), out)
    text = read_plain_text(out)
    for kw in ("安全验算书", "一、参数卡", "二、逐项验算", "三、中间量",
               "四、结论汇总", "五、签署栏（手填）", "立杆稳定性",
               "lizhigan_stability", "0.2814", "JGJ130"):
        assert kw in text, kw
    # 免责声明强制：整段原文在文中；内容无时间戳（签署栏手填）
    assert DISCLAIMER in text
    assert "2026-10" not in text


def test_calc_report_fail_path_lists_fails(tmp_path):
    """不合格路径算例：报告结论汇总应列出 fail 项（不粉饰）。"""
    path = os.path.join(DATA_DIR, "examples", "EX-lizhigan-nw-003.json")
    with open(path, encoding="utf-8") as f:
        example = json.load(f)
    knowledge = load_knowledge(DATA_DIR)
    out = str(tmp_path / "calc-fail.docx")
    generate_calc_report(example["input_card"],
                         run_calc("M-1", example["input_card"], knowledge), out)
    text = read_plain_text(out)
    assert "不满足" in text
    assert "1.0133" in text
    assert_no_external_links(out)


def test_calc_report_blocked_renders_note_only(tmp_path):
    """blocked（依据未核对）：无任何计算数值，仅载说明。"""
    result = blocked_result("M-1", ["F-JGJ130-5.2.5-n", "T-JGJ130-demo"])
    out = str(tmp_path / "calc-blocked.docx")
    generate_calc_report({"category": "coupler_steel_pipe_scaffold"}, result, out)
    text = read_plain_text(out)
    assert "不可验算（依据未核对）" in text
    assert "F-JGJ130-5.2.5-n" in text
    assert "lizhigan_stability" not in text
    assert DISCLAIMER in text
    assert_no_external_links(out)
