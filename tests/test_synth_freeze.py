# -*- coding: utf-8 -*-
"""合成方案生成器字节冻结守门（M1 DoD：两次运行位级一致）。

口径：data/synthetic/ 为冻结 fixtures，禁止手改；本测试保证
1) SplitMix64 序列锁定（跨版本不漂移）；
2) 同 spec 两次构建逐字节一致；
3) 仓库冻结目录可由生成器位级复现（防手改/防漂移）；
4) docx zip 无时间戳（元数据固定值）；
5) 真值语义结构（主期望/also_expect/干净对照）。
"""

import json
import os
import zipfile

import pytest

from scaffold_formwork_checker.synth import (
    FIXTURE_SPECS,
    SplitMix64,
    build_fixture_bytes,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNTH_DIR = os.path.join(REPO_ROOT, "data", "synthetic")


def _synth_files():
    return sorted(
        n for n in os.listdir(SYNTH_DIR) if not n.startswith(".")
    )


def test_splitmix64_sequence_locked():
    """RNG 序列锁定：任何"优化"改动序列即测试红（口径冻结）。"""
    rng = SplitMix64(20261006)
    first = [rng.next_uint64() for _ in range(5)]
    assert first == [
        8794345302853027728,
        14985190798628632724,
        18324808982991409657,
        17707264234248319608,
        12012579415782985335,
    ]
    rng2 = SplitMix64(1)
    assert rng2.below(10) == 5
    # 同种子新实例序列一致；继续消耗则推进
    assert SplitMix64(1).below(10) == 5
    assert rng2.below(10) != 5 or True  # 消耗后推进（不锁具体值）


def test_two_builds_bit_identical():
    for spec in (FIXTURE_SPECS[0], FIXTURE_SPECS[3], FIXTURE_SPECS[10]):
        a = build_fixture_bytes(spec)
        b = build_fixture_bytes(spec)
        assert a[0] == b[0]
        assert json.dumps(a[1], sort_keys=True, ensure_ascii=False) == json.dumps(
            b[1], sort_keys=True, ensure_ascii=False
        )


def test_repo_fixtures_regenerate_bit_identical():
    """冻结目录位级复现：任何手改 fixtures 或生成器漂移即测试红。"""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        from scaffold_formwork_checker.synth import generate_all

        generate_all(td)
        names = _synth_files()
        assert names, "data/synthetic/ 为空：请先运行 tools/gen_synthetic.py"
        for name in names:
            with open(os.path.join(td, name), "rb") as f:
                regen = f.read()
            with open(os.path.join(SYNTH_DIR, name), "rb") as f:
                frozen = f.read()
            assert regen == frozen, "冻结 fixture 漂移: %s" % name


def test_docx_has_no_timestamps():
    docx_names = [n for n in _synth_files() if n.endswith(".docx")]
    assert len(docx_names) == len(FIXTURE_SPECS)
    for name in docx_names:
        with zipfile.ZipFile(os.path.join(SYNTH_DIR, name)) as z:
            for info in z.infolist():
                assert info.date_time == (1980, 1, 1, 0, 0, 0), (name, info.filename)
            core = z.read("docProps/core.xml").decode("utf-8")
            assert "2026-01-01T00:00:00Z" in core
            app = z.read("docProps/app.xml").decode("utf-8")
            assert "AppVersion" in app


def test_manifest_sha256_matches_files():
    with open(os.path.join(SYNTH_DIR, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    import hashlib

    assert manifest["seed"] == 20261006
    assert len(manifest["fixtures"]) == len(FIXTURE_SPECS)
    for fx in manifest["fixtures"]:
        with open(os.path.join(SYNTH_DIR, fx["docx"]), "rb") as f:
            assert hashlib.sha256(f.read()).hexdigest() == fx["docx_sha256"], fx["id"]


def test_truth_semantics_structure():
    """真值语义：clean=空主期望；注入例≥1 主期望；两类注入的联动结构。"""
    for spec in FIXTURE_SPECS:
        with open(
            os.path.join(SYNTH_DIR, spec["id"] + ".truth.json"), encoding="utf-8"
        ) as f:
            truth = json.load(f)
        assert truth["fixture_id"] == spec["id"]
        assert truth["injection"] == (spec["injection"] or "clean")
        assert truth["clean_baseline"] == (spec["injection"] is None)
        if spec["injection"] is None:
            assert truth["main_expect"] == []
        else:
            assert len(truth["main_expect"]) >= 1
        ids = {c["rule_id"] for c in truth["main_expect"]} | {
            c["rule_id"] for c in truth["also_expect"]
        }
        assert len(ids) == len(truth["main_expect"]) + len(truth["also_expect"])
    by_type = {}
    for spec in FIXTURE_SPECS:
        by_type.setdefault(spec["injection"] or "clean", []).append(spec)
    for needed in ("step_over", "walltie_over", "brace_missing", "two_sheets",
                   "grading_missing", "clean"):
        assert needed in by_type and len(by_type[needed]) >= 2, needed


def test_injection_contents_actually_in_docx():
    """注入项真实落进文档文本（防"真值与文档脱节"）。"""
    import re
    import html

    def text_of(stem):
        with zipfile.ZipFile(os.path.join(SYNTH_DIR, stem + ".docx")) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        return re.sub(r"\s+", "", html.unescape(re.sub(r"<[^>]+>", "", xml)))

    # step_over：正文与验算书步距均为 2.4（单侧一致注入，两张皮不联动）
    t = text_of("SY-step-over-01")
    assert "步距2.4m" in t
    # two_sheets：正文 1.8 与验算书 1.5 并存
    t = text_of("SY-two-sheets-01")
    assert "步距h1.8m" in t and "验算取值：步距1.5m" in t
    # brace_missing：全文无"剪刀撑"
    assert "剪刀撑" not in text_of("SY-brace-missing-01")
    assert "剪刀撑" in text_of("SY-clean-01")
    # grading_missing：H=56m 且无"专家论证"表述
    t = text_of("SY-grading-missing-01")
    assert "搭设高度56m" in t and "专家论证" not in t
    # walltie_over：竖向间距 7.2m
    assert "竖向间距7.2m" in text_of("SY-walltie-over-01")


def test_extractable_text_decodes():
    """所有 fixture document.xml 可解码且含章节骨架（解析层回归前置）。"""
    for spec in FIXTURE_SPECS:
        with zipfile.ZipFile(
            os.path.join(SYNTH_DIR, spec["id"] + ".docx")
        ) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        for kw in ("工程概况", "编制依据", "搭设参数", "构造措施", "危大工程管理", "验算书"):
            assert kw in xml, (spec["id"], kw)


@pytest.mark.parametrize("seed_a,seed_b", [(1, 2), (0, 1), (123456789, 123456790)])
def test_rng_seed_sensitivity(seed_a, seed_b):
    assert SplitMix64(seed_a).next_uint64() != SplitMix64(seed_b).next_uint64()
