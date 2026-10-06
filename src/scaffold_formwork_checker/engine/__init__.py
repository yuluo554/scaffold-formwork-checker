# -*- coding: utf-8 -*-
"""M2 公式引擎：5+1 验算模块统一入口。

契约（plan/04 §3）：calc(card: ParamCard, kn: Knowledge) -> CalcResult。
- verdict 只由确定性比较产生（ratio ≤ 1 → pass）；
- 任一依赖条目 status=待核对 → 整模块返回"不可验算（依据未核对）"；
- 零 LLM 通路、零第三方依赖（纯 Python + math）。
"""

from .card import CardError, ParamCard
from .loader import Knowledge, KnowledgeError, load_knowledge
from .m_beams import calc_m3
from .m_formwork import calc_m6
from .m_foundation import calc_m5
from .m_stability import calc_m1, calc_m2
from .m_walltie import calc_m4
from .result import blocked_result, make_check, make_result
from .tables import TableLookupError, verify_anchors

MODULES = {
    "M-1": calc_m1,
    "M-2": calc_m2,
    "M-3": calc_m3,
    "M-4": calc_m4,
    "M-5": calc_m5,
    "M-6": calc_m6,
}

MODULE_NAMES = {
    "M-1": "立杆稳定性（不组合风，JGJ130）",
    "M-2": "立杆稳定性（组合风，JGJ130）",
    "M-3": "纵/横向水平杆（抗弯+挠度+扣件抗滑，JGJ130）",
    "M-4": "连墙件（强度+稳定+扣件抗滑，JGJ130）",
    "M-5": "立杆地基承载力（JGJ130）",
    "M-6": "模板支架立柱稳定/地基（JGJ162）",
}


def detect_module(card):
    """按参数卡内容自动识别验算模块（显式 --module 优先于本函数）。"""
    if not isinstance(card, dict):
        raise CardError("参数卡须为 JSON 对象，得到 %s" % type(card).__name__)
    category = card.get("category")
    if category == "formwork_support":
        return "M-6"
    if category != "coupler_steel_pipe_scaffold":
        raise CardError(
            "无法识别 category=%r（须为 coupler_steel_pipe_scaffold / formwork_support），"
            "请用 --module 显式指定" % (category,))
    if card.get("foundation") is not None:
        return "M-5"
    if card.get("member") in ("cross", "long"):
        return "M-3"
    if card.get("tie_length_m") is not None or card.get("tie_type") is not None:
        return "M-4"
    if card.get("wind", "不组合") == "不组合":
        return "M-1"
    return "M-2"


def run_calc(module_id, card_data, knowledge):
    """校验参数卡并运行指定模块。CardError/KnowledgeError 由调用方按输入错误处置。"""
    if module_id not in MODULES:
        raise CardError("未知验算模块 %r（可选：%s）" % (module_id, ", ".join(MODULES)))
    card = ParamCard(card_data, module_id)
    return MODULES[module_id](card, knowledge)


__all__ = [
    "MODULES", "MODULE_NAMES", "detect_module", "run_calc",
    "ParamCard", "CardError", "Knowledge", "KnowledgeError", "load_knowledge",
    "blocked_result", "make_check", "make_result", "TableLookupError", "verify_anchors",
]
