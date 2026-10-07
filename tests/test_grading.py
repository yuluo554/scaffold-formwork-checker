# -*- coding: utf-8 -*-
"""M3 危大分级判定器守门。

M3 DoD ②：分级边界值用例 100%（23.9/24.0/24.1、49.9/50.0/50.1 及其余条目
阈值 ±ε）；类型识别覆盖 panorama 全部 9 条目；参数缺失 → 待人工确认（三值
逻辑：OR 短路出确定结论，否则 pending）。
"""

import pytest

from scaffold_formwork_checker.engine.loader import KnowledgeError
from scaffold_formwork_checker.grading import (
    eval_cond,
    judge,
    load_panorama,
    recognize_item,
)

PANORAMA = load_panorama()
ITEM_IDS = {item["item_id"] for item in PANORAMA["items"]}


def _luodi(height):
    return judge("pan-luodi-gangguan-24", {"build_height": height})


# ---- 边界值（落地架 24m/50m 两档）----

@pytest.mark.parametrize("height,level", [
    (23.9, "none"), (24.0, "weida"), (24.1, "weida"),
    (49.9, "weida"), (50.0, "chaoguimo"), (50.1, "chaoguimo"),
    (0.0, "none"), (12.0, "none"), (30.0, "weida"), (56.0, "chaoguimo"),
])
def test_luodi_boundary_values(height, level):
    r = _luodi(height)
    assert r["status"] == "definite"
    assert r["level"] == level
    assert r["verdict"] == ("pass" if level == "none" else "triggered")


def test_luodi_chaoguimo_duty_and_rule_id():
    r = _luodi(56.0)
    assert r["rule_id"] == "G-pan-luodi-50"
    assert "专家论证" in r["duty"]
    assert r["label"] == "超过一定规模的危大工程"
    assert r["basis"], "依据摘录必须非空"
    assert all("31号" in b["doc"] for b in r["basis"])


def test_luodi_weida_rule_id_and_duty():
    r = _luodi(30.0)
    assert r["rule_id"] == "G-pan-luodi-24"
    assert "专项施工方案" in r["duty"]


# ---- 其余条目边界值 ----

@pytest.mark.parametrize("item,params,level", [
    ("pan-xuantiao-jiaoshoujia", {"segment_height": 19.9}, "weida"),
    ("pan-xuantiao-jiaoshoujia", {"segment_height": 20.0}, "chaoguimo"),
    ("pan-xuantiao-jiaoshoujia", {"segment_height": 20.1}, "chaoguimo"),
    ("pan-fuzhuo-shengjiang", {"lift_height": 149.9}, "weida"),
    ("pan-fuzhuo-shengjiang", {"lift_height": 150.0}, "chaoguimo"),
    ("pan-fuzhuo-shengjiang", {"lift_height": 150.1}, "chaoguimo"),
    ("pan-chengzhong-zhicheng", {"single_point_load": 6.9}, "weida"),
    ("pan-chengzhong-zhicheng", {"single_point_load": 7.0}, "chaoguimo"),
    ("pan-chengzhong-zhicheng", {"single_point_load": 7.1}, "chaoguimo"),
])
def test_other_items_boundary_values(item, params, level):
    r = judge(item, params)
    assert r["status"] == "definite"
    assert r["level"] == level


def _muban(height=0.1, span=0.1, total=0.1, linear=0.1, independent=False):
    return {"support_height": height, "support_span": span,
            "total_load_design": total, "linear_load_design": linear,
            "independent_member": independent}


@pytest.mark.parametrize("params,level", [
    (_muban(), "none"),
    (_muban(height=4.9), "none"),
    (_muban(height=5.0), "weida"),
    (_muban(span=9.9), "none"),
    (_muban(span=10.0), "weida"),
    (_muban(span=18.0), "chaoguimo"),
    (_muban(total=9.9), "none"),
    (_muban(total=10.0), "weida"),
    (_muban(total=15.0), "chaoguimo"),
    (_muban(linear=14.9), "none"),
    (_muban(linear=15.0), "weida"),
    (_muban(linear=20.0), "chaoguimo"),
    (_muban(independent=True), "weida"),
    (_muban(height=8.0), "chaoguimo"),
])
def test_muban_five_conditions_and_level_precedence(params, level):
    """危大 5 条件为 OR；超规模 4 条件为 OR；chaoguimo 优先于 weida。"""
    r = judge("pan-muban-zhicheng", params)
    assert r["status"] == "definite"
    assert r["level"] == level


def test_type_triggered_items_are_weida_without_height():
    """类型即危大条目（吊篮/卸料平台/异型/工具式模板）：无高度参数也出确定结论。"""
    for item in ("pan-gaochudiaolan", "pan-xieliao-pingtai",
                 "pan-yixing-jiaoshoujia", "pan-gongjushi-muban"):
        r = judge(item, {})
        assert r["status"] == "definite", item
        assert r["level"] == "weida", item


# ---- 类型识别（覆盖全部 9 条目）----

def test_recognize_item_covers_all_panorama_items():
    texts = {
        "pan-luodi-gangguan-24": "某工程 落地式扣件钢管脚手架专项施工方案",
        "pan-fuzhuo-shengjiang": "附着式升降脚手架工程专项施工方案",
        "pan-xuantiao-jiaoshoujia": "悬挑式脚手架专项施工方案",
        "pan-gaochudiaolan": "高处作业吊篮专项施工方案",
        "pan-xieliao-pingtai": "卸料平台、操作平台工程专项施工方案",
        "pan-yixing-jiaoshoujia": "异型脚手架工程专项施工方案",
        "pan-gongjushi-muban": "滑模、爬模工具式模板工程专项施工方案",
        "pan-muban-zhicheng": "混凝土模板支撑工程专项施工方案",
        "pan-chengzhong-zhicheng": "钢结构安装满堂支撑体系（承重支撑）方案",
    }
    assert set(texts) == ITEM_IDS
    for item_id, text in texts.items():
        assert recognize_item(text) == item_id, text


def test_recognize_item_unknown_returns_none():
    assert recognize_item("基坑支护及土方开挖专项施工方案") is None
    assert recognize_item("") is None


# ---- 待人工确认（参数缺失/依据未核对/条目不存在）----

def test_missing_params_pending():
    r = judge("pan-luodi-gangguan-24", {})
    assert r["status"] == "pending"
    assert r["unknown_params"] == ["build_height"]


def test_partial_params_kleene_or_can_still_decide():
    """三值逻辑：超规模条件已有真值命中 → OR 短路出确定结论。"""
    r = judge("pan-muban-zhicheng", {"support_height": 8.0})
    assert r["status"] == "definite"
    assert r["level"] == "chaoguimo"
    # 未命中且其余参数缺失 → pending
    r = judge("pan-muban-zhicheng", {"support_height": 3.0})
    assert r["status"] == "pending"


def test_unknown_item_pending():
    r = judge("pan-no-such-item", {})
    assert r["status"] == "pending"


def test_unverified_basis_pending(monkeypatch):
    """分级依据待核对 → 不出确定结论（条文纪律）。"""
    doc = load_panorama()
    doc["items"][0]["basis"][0]["status"] = "待核对"
    r = judge("pan-luodi-gangguan-24", {"build_height": 56.0}, panorama=doc)
    assert r["status"] == "pending"
    assert "待核对" in r["note"]


# ---- 条件求值器单元 ----

def test_eval_cond_literals_and_suffix():
    assert eval_cond("true", {}) is True
    assert eval_cond("false", {}) is False
    assert eval_cond("false（该类型工程即为危大）", {}) is False


def test_eval_cond_chained_comparison():
    p = {"build_height": 30.0}
    assert eval_cond("24 <= build_height < 50", p) is True
    assert eval_cond("build_height >= 50", p) is False
    assert eval_cond("build_height < 24", p) is False


def test_eval_cond_and_or_not():
    p = {"a": 5.0, "b": 1.0, "flag": False}
    assert eval_cond("a >= 5 && b >= 1", p) is True
    assert eval_cond("a >= 5 || b >= 9", p) is True
    assert eval_cond("!(flag)", p) is True
    assert eval_cond("a >= 5 && !(flag)", p) is True


def test_eval_cond_three_valued():
    p = {"a": 5.0}
    assert eval_cond("a >= 5 || missing >= 1", p) is True    # OR 短路
    assert eval_cond("a >= 9 && missing >= 1", p) is False   # AND 短路
    assert eval_cond("missing >= 1", p) is None              # 缺失传播
    assert eval_cond("a >= 9 || missing >= 1", p) is None


def test_load_panorama_missing_dir_raises():
    with pytest.raises(KnowledgeError):
        load_panorama("no-such-data-dir")
