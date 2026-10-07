# -*- coding: utf-8 -*-
"""M3 解析降级守门：低置信度→unknown_slots→"待人工确认"链路（M3 DoD ④）。

口径：文本路线宁缺勿错——同槽多值冲突强制降级（置信度 0.5 < 0.7）；
表格缺失时表格类参数进 unknown_slots；核查侧跳过并记 confirmation 而非硬判。
"""

import pytest

from scaffold_formwork_checker.engine.loader import load_knowledge
from scaffold_formwork_checker.parse import ParseError, parse_document_text
from scaffold_formwork_checker.parse.card import CONFIDENCE_MIN, SchemeCard
from scaffold_formwork_checker.rules import load_checks_table, run_checks


# ---- SchemeCard 置信度语义 ----

def test_low_confidence_slot_goes_to_unknown_slots():
    card = SchemeCard("scheme")
    assert card.set("step", 1.8, unit="m", confidence=0.5) is False
    assert card.unknown_slots == ["step"]
    assert not card.is_known("step")
    assert CONFIDENCE_MIN == 0.7


def test_boundary_confidence_is_known():
    card = SchemeCard("scheme")
    assert card.set("step", 1.8, unit="m", confidence=CONFIDENCE_MIN) is True
    assert card.is_known("step")


def test_none_value_goes_to_unknown_slots():
    card = SchemeCard("scheme")
    card.set("build_height", None, unit="m", confidence=0.85)
    assert "build_height" in card.unknown_slots


# ---- 抽取层降级 ----

def _doc(lines, tables=None):
    return {"paragraphs": [{"style": "", "text": t} for t in lines],
            "tables": tables or []}


def test_ambiguous_build_height_degrades():
    """同槽多值冲突（正文两处搭设高度不一致）→ unknown_slots，不猜值。"""
    doc = _doc([
        "某工程 落地式扣件钢管脚手架专项施工方案",
        "一、工程概况",
        "本工程为框架结构，搭设高度12 m，随主体结构逐层搭设。",
        "五、危大工程管理",
        "本工程搭设高度18 m，未达到24m，按常规安全管理执行。",
    ])
    parsed = parse_document_text(doc["paragraphs"], doc["tables"], doc_name="x.docx")
    card = parsed.scheme_card
    assert card.value("build_height") is None
    assert "build_height" in card.unknown_slots


def test_missing_params_table_degrades_table_slots():
    """无参数表（纯文本体例）→ 表格类参数全部 unknown_slots，高度/关键词仍可提取。"""
    doc = _doc([
        "某工程 落地式扣件钢管脚手架专项施工方案",
        "一、工程概况",
        "脚手架采用落地式扣件钢管脚手架（双排），搭设高度12 m。",
        "四、构造措施",
        "3. 剪刀撑：外侧全立面连续设置剪刀撑。",
    ])
    parsed = parse_document_text(doc["paragraphs"], doc["tables"], doc_name="x.docx")
    card = parsed.scheme_card
    assert card.value("build_height") == 12.0
    assert card.value("scissor_brace") is True
    for slot in ("step", "long_spacing", "cross_spacing", "wall_tie_v"):
        assert slot in card.unknown_slots
    assert card.value("rows") == "double"


def test_empty_document_degrades_everything():
    parsed = parse_document_text([], [], doc_name="empty.docx")
    card = parsed.scheme_card
    assert "build_height" in card.unknown_slots
    assert card.project_type == ""


# ---- 降级如何传导到核查：跳过 + 待人工确认，而非硬判 ----

def test_unknown_slot_rules_become_confirmations_not_violations():
    """step/搭设高度均未解析 → 步距规则不判违规记 confirmation；分级 pending。"""
    doc = _doc([
        "某工程 落地式扣件钢管脚手架专项施工方案",
        "一、工程概况",
        "脚手架采用落地式扣件钢管脚手架（双排），未注明具体搭设参数。",
    ])
    parsed = parse_document_text(doc["paragraphs"], doc["tables"], doc_name="x.docx")
    calcbook = parse_document_text([], [], doc_name="x.docx").scheme_card
    report = run_checks(parsed.scheme_card, calcbook, load_knowledge(),
                        load_checks_table())
    rule_ids = {f["rule_id"] for f in report["findings"]}
    assert "R-step-limit" not in rule_ids
    conf_params = {c["rule_id"]: c for c in report["confirmations"]}
    assert "R-step-limit" in conf_params
    assert "未解析" in conf_params["R-step-limit"]["reason"]
    # 分级参数缺失 → pending → 分级确认项
    assert any(c["rule_id"] == "G-grading" for c in report["confirmations"])
    assert report["grading"]["status"] == "pending"


def test_pdf_reader_rejects_non_pdf(tmp_path):
    """PDF 通路输入守门：非 PDF 文件 → ParseError（exit 2 语义）。"""
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    from scaffold_formwork_checker.parse import parse_scheme
    with pytest.raises(ParseError):
        parse_scheme(str(bad))


def test_parse_scheme_rejects_unsupported_extension(tmp_path):
    from scaffold_formwork_checker.parse import parse_scheme
    doc = tmp_path / "scheme.doc"
    doc.write_bytes(b"legacy")
    with pytest.raises(ParseError) as excinfo:
        parse_scheme(str(doc))
    assert "docx" in str(excinfo.value)


def test_parse_scheme_missing_file():
    from scaffold_formwork_checker.parse import parse_scheme
    with pytest.raises(ParseError):
        parse_scheme("no-such-file.docx")
