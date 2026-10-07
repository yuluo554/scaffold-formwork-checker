# -*- coding: utf-8 -*-
"""M3 解析器守门：12 冻结 fixtures → 方案卡/验算书卡字段级对账。

期望值直接取自生成器文本要素（synth/generator._scheme_texts，与 docx 落盘
内容同源），逐 fixture 全字段对账：
- 全部 12 例 unknown_slots 必须为空（冻结体例可被文本路线完整解析）；
- two_sheets 注入：验算书卡步距与方案卡不一致（解析层就把两卡分开）。
"""

import json
import os

from scaffold_formwork_checker.parse import parse_scheme
from scaffold_formwork_checker.synth import FIXTURE_SPECS, SplitMix64
from scaffold_formwork_checker.synth.generator import FIXTURE_SEED, _scheme_texts

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNTH_DIR = os.path.join(REPO_ROOT, "data", "synthetic")

_WALL_TIE_ENUM = {"两步三跨": "two_step_three_span", "三步三跨": "three_step_three_span"}

_LENGTH_FIELDS = ("build_height", "step", "long_spacing", "cross_spacing",
                  "wall_tie_v", "wall_tie_h")


def _scheme(spec):
    """复现该 fixture 的文本要素（与 build_fixture_bytes 同一 rng 路径）。"""
    rng = SplitMix64(FIXTURE_SEED + FIXTURE_SPECS.index(spec))
    return _scheme_texts(spec, rng)


def _parse(spec):
    return parse_scheme(os.path.join(SYNTH_DIR, spec["id"] + ".docx"))


def test_all_fixtures_parse_without_unknown_slots():
    for spec in FIXTURE_SPECS:
        parsed = _parse(spec)
        assert parsed.scheme_card.unknown_slots == [], spec["id"]
        assert parsed.calcbook_card.unknown_slots == [], spec["id"]
        assert parsed.scheme_card.card_type == "scheme"
        assert parsed.calcbook_card.card_type == "calcbook"


def test_scheme_card_fields_match_generator_body():
    for spec in FIXTURE_SPECS:
        scheme = _scheme(spec)
        card = _parse(spec).scheme_card
        expected = {
            "build_height": scheme["build_height"],
            "step": scheme["step"],
            "long_spacing": scheme["long_spacing"],
            "cross_spacing": scheme["cross_spacing"],
            "wall_tie": _WALL_TIE_ENUM[scheme["wall_tie"]],
            "wall_tie_v": scheme["wall_tie_v"],
            "wall_tie_h": scheme["wall_tie_h"],
            "pipe_spec": "48.3x3.6",
            "rows": "double",
            "board_layers": scheme["board_layers"],
            "live_load": scheme["live"],
            # 关键词在位=文本实际写入条件（生成器只在对应高度分支落文字）
            "scissor_brace": scheme["mention_brace"],
            "expert_review": (scheme["build_height"] >= 50.0
                              and scheme["mention_expert_review"]),
            "special_plan": scheme["build_height"] >= 24.0,
        }
        for name, want in expected.items():
            got = card.value(name)
            assert got == want, (spec["id"], name, got, want)
        unit = card.entries["step"]["unit"]
        for name in _LENGTH_FIELDS:
            assert card.entries[name]["unit"] == "m", (spec["id"], name)


def test_project_type_and_category_recognized():
    parsed = _parse(FIXTURE_SPECS[0])
    card = parsed.scheme_card
    assert "专项施工方案" in card.project_type
    assert "落地" in card.project_type
    assert card.category == "coupler_steel_pipe_scaffold"


def test_calcbook_card_split_from_scheme_two_sheets():
    """two_sheets 注入：验算书卡步距 ≠ 方案卡步距；其余 fixtures 两卡一致。"""
    for spec in FIXTURE_SPECS:
        scheme = _scheme(spec)
        parsed = _parse(spec)
        assert parsed.calcbook_card.value("step") == scheme["calc_step"], spec["id"]
        same = parsed.scheme_card.value("step") == parsed.calcbook_card.value("step")
        assert same == (spec["injection"] != "two_sheets"), spec["id"]


def test_entries_carry_confidence_and_evidence():
    parsed = _parse(FIXTURE_SPECS[0])
    entry = parsed.scheme_card.entries["step"]
    assert entry["unit"] == "m"
    assert entry["confidence"] >= 0.7
    assert entry["evidence"].get("locator")
    assert entry["evidence"].get("quote")


def test_to_dict_roundtrip():
    parsed = _parse(FIXTURE_SPECS[0])
    data = parsed.scheme_card.to_dict()
    assert data["card_type"] == "scheme"
    assert set(data["entries"]) >= {"step", "build_height", "wall_tie_v"}
    assert data["unknown_slots"] == []
    restored = json.loads(json.dumps(data, ensure_ascii=False))
    assert restored["entries"]["step"]["value"] == data["entries"]["step"]["value"]
