# -*- coding: utf-8 -*-
"""M2 参数卡：验算输入的统一校验入口（plan/04 §1）。

合法性范围校验在卡片构造时执行，非法即拒收（CardError，CLI 映射 exit 2）：
- 结构校验（本文件）：字段存在性、类型、正数性、枚举值——纯数据形态；
- 规范限值校验（模块内、经条款库取值）：如 JGJ162 立柱步距 ≤1.8m
  （T-JGJ162-column-step，status=已核对）——限值必须挂已核对出处才可执行，
  未核对过的"经验上限"一律不加（条文纪律）。
"""

import math

CATEGORIES = ("coupler_steel_pipe_scaffold", "formwork_support")
WALL_TIES = ("two_step_three_span", "three_step_three_span")
PIPE_SPECS = ("48.3x3.6",)
SCAFFOLD_STATES = ("enclosed_net", "semi_enclosed", "open")
MEMBERS = ("cross", "long")


class CardError(ValueError):
    """参数卡非法（缺字段/超范围/坏枚举）。消息面向用户，直接可读。"""


def _require(card, key, module_hint):
    if key not in card or card[key] is None:
        raise CardError("缺少必填参数 %s（%s）" % (key, module_hint))
    return card[key]


def _positive_number(value, key):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CardError("参数 %s 须为数值，得到 %r" % (key, value))
    if not math.isfinite(value):
        raise CardError("参数 %s 须为有限数值，得到 %r" % (key, value))
    if value <= 0:
        raise CardError("参数 %s 须为正数，得到 %r" % (key, value))
    return float(value)


def _non_negative_number(value, key):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CardError("参数 %s 须为数值，得到 %r" % (key, value))
    if not math.isfinite(value):
        raise CardError("参数 %s 须为有限数值，得到 %r" % (key, value))
    if value < 0:
        raise CardError("参数 %s 不得为负数，得到 %r" % (key, value))
    return float(value)


def _enum(value, key, allowed):
    if value not in allowed:
        raise CardError("参数 %s 须为 %s 之一，得到 %r" % (key, list(allowed), value))
    return value


def _loads(card):
    loads = _require(card, "loads", "荷载参数")
    if not isinstance(loads, dict):
        raise CardError("loads 须为对象，得到 %r" % (loads,))
    return loads


def _common_scaffold(card, require_cross=True):
    """扣件式钢管脚手架公共字段校验，返回规范化片段。

    require_cross=False 供 M-4 连墙件使用（Aw 按 3h×3la 计，不需立杆横距）。
    """
    out = {
        "category": _enum(card.get("category"), "category", ("coupler_steel_pipe_scaffold",)),
        "rows": _enum(card.get("rows"), "rows（单排 single/双排 double）", ("single", "double")),
        "step_m": _positive_number(_require(card, "step_m", "几何参数"), "step_m"),
        "long_spacing_m": _positive_number(_require(card, "long_spacing_m", "几何参数"), "long_spacing_m"),
        "pipe_spec": _enum(card.get("pipe_spec", "48.3x3.6"), "pipe_spec（暂只支持 48.3x3.6）", PIPE_SPECS),
    }
    if require_cross:
        out["cross_spacing_m"] = _positive_number(
            _require(card, "cross_spacing_m", "几何参数"), "cross_spacing_m")
    return out


def _wind_not_combined(card, module_hint):
    wind = card.get("wind", "不组合")
    if wind != "不组合":
        raise CardError("%s 参数卡 wind 须为 \"不组合\"，组合风请用对应模块（得到 %r）"
                        % (module_hint, wind))
    return wind


def validate_m1(card):
    """M-1 立杆稳定·不组合风。"""
    out = _common_scaffold(card)
    _wind_not_combined(card, "M-1")
    out["build_height_m"] = _positive_number(
        _require(card, "build_height_m", "M-1 需搭设高度"), "build_height_m")
    out["wall_tie"] = _enum(_require(card, "wall_tie", "M-1 需连墙件布置"),
                            "wall_tie", WALL_TIES)
    loads = _loads(card)
    out["loads"] = {
        # gk 可缺省：缺省时由表A.0.1 按（步距,纵距,排数）查取
        "gk_struct_kN_per_m": (
            _positive_number(loads["gk_struct_kN_per_m"], "loads.gk_struct_kN_per_m")
            if loads.get("gk_struct_kN_per_m") is not None else None),
        "board_kN_per_m2": _non_negative_number(loads.get("board_kN_per_m2", 0.0), "loads.board_kN_per_m2"),
        "board_layers": _board_layers(loads),
        "rail_kN_per_m": _non_negative_number(loads.get("rail_kN_per_m", 0.0), "loads.rail_kN_per_m"),
        "safety_net_kN_per_m2": _non_negative_number(loads.get("safety_net_kN_per_m2", 0.0), "loads.safety_net_kN_per_m2"),
        "live_kN_per_m2": _positive_number(_require(loads, "live_kN_per_m2", "M-1 荷载"), "loads.live_kN_per_m2"),
    }
    return out


def _board_layers(loads):
    layers = loads.get("board_layers", 0)
    if isinstance(layers, bool) or not isinstance(layers, int) or layers < 0:
        raise CardError("loads.board_layers 须为非负整数，得到 %r" % (layers,))
    return layers


def _wind_dict(card):
    """M-2/M-6 组合风参数校验，返回规范化 wind dict。"""
    wind = _require(card, "wind", "组合风工况")
    if not isinstance(wind, dict):
        raise CardError("组合风工况下 wind 须为对象（w0/mu_z/...），得到 %r" % (wind,))
    out = {}
    if "wk_kN_per_m2" in wind and wind["wk_kN_per_m2"] is not None:
        out["wk_kN_per_m2"] = _positive_number(wind["wk_kN_per_m2"], "wind.wk_kN_per_m2")
        return out
    out["w0_kN_per_m2"] = _positive_number(_require(wind, "w0_kN_per_m2", "风荷载"), "wind.w0_kN_per_m2")
    out["mu_z"] = _positive_number(_require(wind, "mu_z", "风荷载"), "wind.mu_z")
    state = wind.get("scaffold_state", "enclosed_net")
    out["scaffold_state"] = _enum(state, "wind.scaffold_state", SCAFFOLD_STATES)
    out["back_wall"] = wind.get("back_wall")
    if "shape_mu_s" in wind and wind["shape_mu_s"] is not None:
        out["shape_mu_s"] = _positive_number(wind["shape_mu_s"], "wind.shape_mu_s")
    elif wind.get("shape_phi") is not None:
        out["shape_phi"] = _positive_number(wind["shape_phi"], "wind.shape_phi")
    # shape_phi 与 shape_mu_s 均缺省时：敞开式可由表A.0.5 按（步距,纵距）查取，
    # 其余状态必须显式给出（表4.2.6 体型系数依赖挡风系数输入）
    if "shape_mu_s" not in out and "shape_phi" not in out and state != "open":
        raise CardError("wind.shape_phi 缺失：enclosed_net/semi_enclosed 状态须显式给出挡风系数")
    return out


def validate_m2(card):
    """M-2 立杆稳定·组合风。"""
    out = _common_scaffold(card)
    out["wind"] = _wind_dict(card)
    out["build_height_m"] = _positive_number(
        _require(card, "build_height_m", "M-2 需搭设高度"), "build_height_m")
    out["wall_tie"] = _enum(_require(card, "wall_tie", "M-2 需连墙件布置"),
                            "wall_tie", WALL_TIES)
    loads = _loads(card)
    out["loads"] = {
        "gk_struct_kN_per_m": (
            _positive_number(loads["gk_struct_kN_per_m"], "loads.gk_struct_kN_per_m")
            if loads.get("gk_struct_kN_per_m") is not None else None),
        "board_kN_per_m2": _non_negative_number(loads.get("board_kN_per_m2", 0.0), "loads.board_kN_per_m2"),
        "board_layers": _board_layers(loads),
        "rail_kN_per_m": _non_negative_number(loads.get("rail_kN_per_m", 0.0), "loads.rail_kN_per_m"),
        "safety_net_kN_per_m2": _non_negative_number(loads.get("safety_net_kN_per_m2", 0.0), "loads.safety_net_kN_per_m2"),
        "live_kN_per_m2": _positive_number(_require(loads, "live_kN_per_m2", "M-2 荷载"), "loads.live_kN_per_m2"),
    }
    return out


def validate_m3(card):
    """M-3 纵/横向水平杆（member=cross 横向简支 / long 纵向三跨连续）。"""
    out = _common_scaffold(card)
    out["member"] = _enum(_require(card, "member", "M-3 需杆件类型"),
                          "member（cross=横向水平杆/long=纵向水平杆）", MEMBERS)
    _wind_not_combined(card, "M-3")
    loads = _loads(card)
    out["loads"] = {
        "board_kN_per_m2": _non_negative_number(loads.get("board_kN_per_m2", 0.0), "loads.board_kN_per_m2"),
        "live_kN_per_m2": _positive_number(_require(loads, "live_kN_per_m2", "M-3 荷载"), "loads.live_kN_per_m2"),
    }
    return out


def validate_m4(card):
    """M-4 连墙件。"""
    out = _common_scaffold(card, require_cross=False)
    out["wall_tie"] = _enum(_require(card, "wall_tie", "M-4 需连墙件布置"),
                            "wall_tie", WALL_TIES)
    tie_type = card.get("tie_type", "steel_pipe_coupler")
    out["tie_type"] = _enum(tie_type, "tie_type（暂只支持钢管扣件 steel_pipe_coupler）",
                            ("steel_pipe_coupler",))
    out["tie_length_m"] = _positive_number(_require(card, "tie_length_m", "M-4 需连墙杆长度"),
                                           "tie_length_m")
    if card.get("build_height_m") is not None:
        out["build_height_m"] = _positive_number(card["build_height_m"], "build_height_m")
    wind = _require(card, "wind", "M-4 风荷载")
    if isinstance(wind, dict):
        out["wind"] = _wind_dict(card)
    else:
        raise CardError("M-4 wind 须为对象（wk_kN_per_m2 或 w0/mu_z/...），得到 %r" % (wind,))
    return out


def _foundation(card):
    foundation = _require(card, "foundation", "地基参数")
    if not isinstance(foundation, dict):
        raise CardError("foundation 须为对象，得到 %r" % (foundation,))
    pad = _require(foundation, "pad_m", "foundation 垫板/垫木尺寸")
    if (not isinstance(pad, (list, tuple)) or len(pad) != 2
            or any(isinstance(x, bool) or not isinstance(x, (int, float)) or x <= 0 for x in pad)):
        raise CardError("foundation.pad_m 须为 [长m, 宽m] 两个正数，得到 %r" % (pad,))
    out = dict(foundation)  # 保留全部原始字段（fgk/reduction/mf/fak/type 等）
    out["pad_m"] = [float(pad[0]), float(pad[1])]
    # 轴力优先取卡上显式值（由解析或上游模块传入）；缺省时须提供完整架体参数现算
    if foundation.get("nk_kN") is not None:
        out["nk_kN"] = _positive_number(foundation["nk_kN"], "foundation.nk_kN")
    if foundation.get("n_design_kN") is not None:
        out["n_design_kN"] = _positive_number(foundation["n_design_kN"], "foundation.n_design_kN")
    return out


def validate_m5(card):
    """M-5 立杆地基承载力（JGJ130 5.5）。

    轴力两条路径：foundation.nk_kN 显式给出（解析/上游模块传入）；
    或给全架体参数（build_height/step/间距/rows/loads）按标准组合（分项系数 1.0）现算。
    """
    if card.get("category") != "coupler_steel_pipe_scaffold":
        raise CardError("M-5 参数卡 category 须为 coupler_steel_pipe_scaffold，得到 %r"
                        % (card.get("category"),))
    foundation = _foundation(card)
    fgk = _require(foundation, "fgk_kPa", "M-5 地基承载力特征值")
    reduction = foundation.get("reduction")
    if reduction is None:
        raise CardError("M-5 缺 foundation.reduction（地基承载力取值系数，"
                        "回填土按 T-JGJ130-fg-reduction 取 0.4，天然地基取 1.0）")
    foundation["fgk_kPa"] = _positive_number(fgk, "foundation.fgk_kPa")
    foundation["reduction"] = _positive_number(reduction, "foundation.reduction")
    foundation["soil_type"] = foundation.get("type", "天然地基")
    out = {
        "category": "coupler_steel_pipe_scaffold",
        "foundation": foundation,
        "pipe_spec": _enum(card.get("pipe_spec", "48.3x3.6"), "pipe_spec（暂只支持 48.3x3.6）", PIPE_SPECS),
    }
    if "nk_kN" in foundation or "n_design_kN" in foundation:
        return out
    # 现算路径：需要与 M-1 相同的架体荷载参数集
    for key in ("build_height_m", "step_m", "long_spacing_m", "cross_spacing_m", "rows"):
        if card.get(key) is None:
            raise CardError(
                "M-5 缺 foundation.nk_kN，须提供完整架体参数（%s 等）现算轴力标准值" % key)
    out["build_height_m"] = _positive_number(card["build_height_m"], "build_height_m")
    out["step_m"] = _positive_number(card["step_m"], "step_m")
    out["long_spacing_m"] = _positive_number(card["long_spacing_m"], "long_spacing_m")
    out["cross_spacing_m"] = _positive_number(card["cross_spacing_m"], "cross_spacing_m")
    out["rows"] = _enum(card["rows"], "rows（单排 single/双排 double）", ("single", "double"))
    out["wall_tie"] = _enum(card.get("wall_tie", "two_step_three_span"), "wall_tie", WALL_TIES)
    loads = _loads(card)
    out["loads"] = {
        "gk_struct_kN_per_m": (
            _positive_number(loads["gk_struct_kN_per_m"], "loads.gk_struct_kN_per_m")
            if loads.get("gk_struct_kN_per_m") is not None else None),
        "board_kN_per_m2": _non_negative_number(loads.get("board_kN_per_m2", 0.0), "loads.board_kN_per_m2"),
        "board_layers": _board_layers(loads),
        "rail_kN_per_m": _non_negative_number(loads.get("rail_kN_per_m", 0.0), "loads.rail_kN_per_m"),
        "safety_net_kN_per_m2": _non_negative_number(loads.get("safety_net_kN_per_m2", 0.0), "loads.safety_net_kN_per_m2"),
        "live_kN_per_m2": _non_negative_number(loads.get("live_kN_per_m2", 0.0), "loads.live_kN_per_m2"),
    }
    if out["loads"]["live_kN_per_m2"] <= 0 and out["loads"]["board_kN_per_m2"] <= 0:
        raise CardError("M-5 现算路径下 loads.live_kN_per_m2 与 board_kN_per_m2 不能同时为 0")
    return out


def validate_m6(card):
    """M-6 模板支架立杆稳定 / 立柱地基（JGJ162）。"""
    if card.get("category") != "formwork_support":
        raise CardError("M-6 参数卡 category 须为 formwork_support，得到 %r" % (card.get("category"),))
    if "foundation" in card and card["foundation"] is not None:
        return _validate_m6_foundation(card)
    return _validate_m6_column(card)


def _validate_m6_column(card):
    wind = card.get("wind", "不组合")
    if wind != "不组合" and not isinstance(wind, dict):
        raise CardError("M-6 wind 须为 \"不组合\" 或风荷载对象，得到 %r" % (wind,))
    spacing = _require(card, "pole_spacing_m", "M-6 立杆间距")
    if (not isinstance(spacing, (list, tuple)) or len(spacing) != 2
            or any(isinstance(x, bool) or not isinstance(x, (int, float)) or x <= 0 for x in spacing)):
        raise CardError("pole_spacing_m 须为 [la, lb] 两个正数，得到 %r" % (spacing,))
    loads = _loads(card)
    out = {
        "category": "formwork_support",
        "step_m": _positive_number(_require(card, "step_m", "M-6 步距"), "step_m"),
        "pole_spacing_m": [float(spacing[0]), float(spacing[1])],
        "pipe_spec": _enum(card.get("pipe_spec", "48.3x3.6"), "pipe_spec（暂只支持 48.3x3.6）", PIPE_SPECS),
        "slab_thickness_m": _positive_number(_require(card, "slab_thickness_m", "M-6 板厚"), "slab_thickness_m"),
        "story_height_m": _positive_number(card.get("story_height_m", 4.0), "story_height_m"),
        "wind": _wind_dict(card) if isinstance(wind, dict) else "不组合",
        "loads": {
            "g1k_kN_per_m2": _non_negative_number(_require(loads, "g1k_kN_per_m2", "M-6 荷载"), "loads.g1k_kN_per_m2"),
            "concrete_kN_per_m3": _positive_number(_require(loads, "concrete_kN_per_m3", "M-6 荷载"), "loads.concrete_kN_per_m3"),
            "rebar_kN_per_m3_slab": _non_negative_number(loads.get("rebar_kN_per_m3_slab", 0.0), "loads.rebar_kN_per_m3_slab"),
            "q1k_kN_per_m2": _non_negative_number(_require(loads, "q1k_kN_per_m2", "M-6 荷载"), "loads.q1k_kN_per_m2"),
        },
    }
    return out


def _validate_m6_foundation(card):
    foundation = _foundation(card)
    if "n_design_kN" not in foundation and "nk_kN" not in foundation:
        raise CardError("M-6 地基验算缺 foundation.n_design_kN（立柱传至垫木顶面轴向力设计值；"
                        "可由 M-6 立杆稳定模块结果传入）")
    out = {
        "category": "formwork_support",
        "foundation": foundation,
    }
    mf = foundation.get("mf")
    if mf is None:
        raise CardError("M-6 地基验算缺 foundation.mf（立柱垫木地基土承载力折减系数，"
                        "按表5.2.6 取值）")
    out["foundation"]["mf"] = _positive_number(mf, "foundation.mf")
    fak = _require(foundation, "fak_kPa", "M-6 地基土承载力")
    out["foundation"]["fak_kPa"] = _positive_number(fak, "foundation.fak_kPa")
    return out


_VALIDATORS = {
    "M-1": validate_m1,
    "M-2": validate_m2,
    "M-3": validate_m3,
    "M-4": validate_m4,
    "M-5": validate_m5,
    "M-6": validate_m6,
}


class ParamCard(object):
    """已校验参数卡：构造即校验，非法拒收（plan/04 §1）。"""

    def __init__(self, data, module_id):
        if not isinstance(data, dict):
            raise CardError("参数卡须为 JSON 对象，得到 %s" % type(data).__name__)
        validator = _VALIDATORS.get(module_id)
        if validator is None:
            raise CardError("未知验算模块 %r（可选 M-1~M-6）" % (module_id,))
        self.module_id = module_id
        self.raw = dict(data)
        self.data = validator(data)

    def __getitem__(self, key):
        return self.data[key]

    def get(self, key, default=None):
        return self.data.get(key, default)

    def __contains__(self, key):
        return key in self.data
