# -*- coding: utf-8 -*-
"""验算页动态表单的字段规格（零 Qt 依赖，plan/04 §8 页签 1）。

- MODULE_DEFAULTS：各模块默认参数卡——数值转录自 data/examples/ 算例
  （已知可过引擎校验），默认卡必须能直接跑通 run_calc（tests 锁定防漂移）；
- FIELD_SPECS：表单字段表（path=参数卡内点路径）；
- assemble()：表单取值 → 参数卡 dict（数值转换；空串=缺省交引擎校验）。

字段校验单一事实源是 engine/card.py（ParamCard 构造时拒收）——本模块只做
"文本→类型"转换，不做规范限值判断，避免两处口径漂移。
"""

from ..engine import CardError

MODULE_NAMES = {
    "M-1": "立杆稳定性（不组合风，JGJ130）",
    "M-2": "立杆稳定性（组合风，JGJ130）",
    "M-3": "纵/横向水平杆（JGJ130）",
    "M-4": "连墙件（JGJ130）",
    "M-5": "立杆地基承载力（JGJ130）",
    "M-6": "模板支架立柱稳定/地基（JGJ162）",
}

_ENUM_TIE = (
    ("two_step_three_span", "二步三跨"),
    ("three_step_three_span", "三步三跨"),
)
_ENUM_ROWS = (("double", "双排"), ("single", "单排"))
_ENUM_MEMBER = (("cross", "横向水平杆"), ("long", "纵向水平杆"))
_ENUM_STATE = (
    ("enclosed_net", "全封闭"),
    ("semi_enclosed", "半封闭"),
    ("open", "敞开"),
)

MODULE_DEFAULTS = {
    "M-1": {
        "category": "coupler_steel_pipe_scaffold", "rows": "double",
        "build_height_m": 12.0, "step_m": 1.8, "long_spacing_m": 1.5,
        "cross_spacing_m": 1.05, "wall_tie": "two_step_three_span",
        "pipe_spec": "48.3x3.6", "wind": "不组合",
        "loads": {"gk_struct_kN_per_m": 0.1295, "board_kN_per_m2": 0.3,
                  "board_layers": 2, "rail_kN_per_m": 0.16,
                  "safety_net_kN_per_m2": 0.01, "live_kN_per_m2": 2.0},
    },
    "M-2": {
        "category": "coupler_steel_pipe_scaffold", "rows": "double",
        "build_height_m": 12.0, "step_m": 1.8, "long_spacing_m": 1.5,
        "cross_spacing_m": 1.05, "wall_tie": "two_step_three_span",
        "pipe_spec": "48.3x3.6",
        "wind": {"w0_kN_per_m2": 0.4, "mu_z": 1.0,
                 "scaffold_state": "enclosed_net", "shape_phi": 0.8,
                 "back_wall": "全封闭墙"},
        "loads": {"gk_struct_kN_per_m": 0.1295, "board_kN_per_m2": 0.3,
                  "board_layers": 2, "rail_kN_per_m": 0.16,
                  "safety_net_kN_per_m2": 0.01, "live_kN_per_m2": 2.0},
    },
    "M-3": {
        "category": "coupler_steel_pipe_scaffold", "rows": "double",
        "member": "cross", "step_m": 1.8, "long_spacing_m": 1.5,
        "cross_spacing_m": 1.05, "pipe_spec": "48.3x3.6",
        "loads": {"board_kN_per_m2": 0.3, "live_kN_per_m2": 2.0},
    },
    "M-4": {
        "category": "coupler_steel_pipe_scaffold", "rows": "double",
        "build_height_m": 12.0, "step_m": 1.8, "long_spacing_m": 1.5,
        "wall_tie": "two_step_three_span", "tie_type": "steel_pipe_coupler",
        "tie_length_m": 1.35, "pipe_spec": "48.3x3.6",
        "wind": {"wk_kN_per_m2": 0.1},
    },
    "M-5": {
        "category": "coupler_steel_pipe_scaffold", "pipe_spec": "48.3x3.6",
        "foundation": {"type": "回填土", "fgk_kPa": 180.0, "reduction": 0.4,
                       "pad_m": [0.4, 0.2], "nk_kN": 4.2615},
    },
    "M-6": {
        "category": "formwork_support", "slab_thickness_m": 0.12,
        "story_height_m": 3.9, "step_m": 1.5, "pole_spacing_m": [1.0, 1.0],
        "pipe_spec": "48.3x3.6", "wind": {"wk_kN_per_m2": 0.3},
        "loads": {"g1k_kN_per_m2": 0.75, "concrete_kN_per_m3": 24.0,
                  "rebar_kN_per_m3_slab": 1.1, "q1k_kN_per_m2": 1.0},
    },
}

# 字段规格：path（参数卡点路径）/ label / kind（number|int|enum|text|pair）/
# unit / options（enum 用）/ required（空值是否算缺字段——缺省空值统一交引擎校验）
FIELD_SPECS = {
    "M-1": [
        ("rows", "排数", "enum", None, _ENUM_ROWS),
        ("build_height_m", "搭设高度", "number", "m", None),
        ("step_m", "步距", "number", "m", None),
        ("long_spacing_m", "纵距", "number", "m", None),
        ("cross_spacing_m", "横距", "number", "m", None),
        ("wall_tie", "连墙件布置", "enum", None, _ENUM_TIE),
        ("loads.gk_struct_kN_per_m", "结构自重 gk（可空=查表）", "number", "kN/m", None),
        ("loads.board_kN_per_m2", "脚手板荷载", "number", "kN/m²", None),
        ("loads.board_layers", "脚手板层数", "int", "层", None),
        ("loads.rail_kN_per_m", "栏杆挡脚板", "number", "kN/m", None),
        ("loads.safety_net_kN_per_m2", "安全网", "number", "kN/m²", None),
        ("loads.live_kN_per_m2", "施工活载", "number", "kN/m²", None),
    ],
    "M-2": [
        ("rows", "排数", "enum", None, _ENUM_ROWS),
        ("build_height_m", "搭设高度", "number", "m", None),
        ("step_m", "步距", "number", "m", None),
        ("long_spacing_m", "纵距", "number", "m", None),
        ("cross_spacing_m", "横距", "number", "m", None),
        ("wall_tie", "连墙件布置", "enum", None, _ENUM_TIE),
        ("wind.w0_kN_per_m2", "基本风压 w0", "number", "kN/m²", None),
        ("wind.mu_z", "风压高度变化系数 μz", "number", None, None),
        ("wind.scaffold_state", "脚手架状态", "enum", None, _ENUM_STATE),
        ("wind.shape_phi", "挡风系数 φ（可空=查表）", "number", None, None),
        ("wind.back_wall", "背面状况", "text", None, None),
        ("loads.gk_struct_kN_per_m", "结构自重 gk（可空=查表）", "number", "kN/m", None),
        ("loads.board_kN_per_m2", "脚手板荷载", "number", "kN/m²", None),
        ("loads.board_layers", "脚手板层数", "int", "层", None),
        ("loads.rail_kN_per_m", "栏杆挡脚板", "number", "kN/m", None),
        ("loads.safety_net_kN_per_m2", "安全网", "number", "kN/m²", None),
        ("loads.live_kN_per_m2", "施工活载", "number", "kN/m²", None),
    ],
    "M-3": [
        ("rows", "排数", "enum", None, _ENUM_ROWS),
        ("member", "杆件类型", "enum", None, _ENUM_MEMBER),
        ("step_m", "步距", "number", "m", None),
        ("long_spacing_m", "纵距", "number", "m", None),
        ("cross_spacing_m", "横距", "number", "m", None),
        ("loads.board_kN_per_m2", "脚手板荷载", "number", "kN/m²", None),
        ("loads.live_kN_per_m2", "施工活载", "number", "kN/m²", None),
    ],
    "M-4": [
        ("rows", "排数", "enum", None, _ENUM_ROWS),
        ("step_m", "步距", "number", "m", None),
        ("long_spacing_m", "纵距", "number", "m", None),
        ("wall_tie", "连墙件布置", "enum", None, _ENUM_TIE),
        ("tie_length_m", "连墙杆长度", "number", "m", None),
        ("build_height_m", "搭设高度（可空）", "number", "m", None),
        ("wind.wk_kN_per_m2", "风荷载 wk", "number", "kN/m²", None),
    ],
    "M-5": [
        ("foundation.type", "地基类型", "text", None, None),
        ("foundation.fgk_kPa", "地基承载力特征值 fgk", "number", "kPa", None),
        ("foundation.reduction", "承载力取值系数（回填土0.4/天然1.0）", "number", None, None),
        ("foundation.pad_m", "垫板尺寸 长,宽", "pair", "m", None),
        ("foundation.nk_kN", "立杆轴力标准值 Nk", "number", "kN", None),
    ],
    "M-6": [
        ("slab_thickness_m", "板厚", "number", "m", None),
        ("story_height_m", "层高", "number", "m", None),
        ("step_m", "步距", "number", "m", None),
        ("pole_spacing_m", "立杆间距 la,lb", "pair", "m", None),
        ("wind.wk_kN_per_m2", "风荷载 wk", "number", "kN/m²", None),
        ("loads.g1k_kN_per_m2", "模板自重 g1k", "number", "kN/m²", None),
        ("loads.concrete_kN_per_m3", "混凝土自重", "number", "kN/m³", None),
        ("loads.rebar_kN_per_m3_slab", "钢筋自重（板）", "number", "kN/m³", None),
        ("loads.q1k_kN_per_m2", "施工活载 q1k", "number", "kN/m²", None),
    ],
}


def default_text(module_id, path, kind):
    """默认卡在表单里的文本形态（enum 显示枚举值本身）。"""
    card = MODULE_DEFAULTS[module_id]
    node = card
    for part in path.split("."):
        node = node[part]
    if kind == "pair":
        return ", ".join(_num_text(x) for x in node)
    return _num_text(node)


def _num_text(x):
    if isinstance(x, float) and x == int(x):
        return str(int(x))
    return str(x)


def assemble(module_id, values):
    """表单取值 {path: str} → 参数卡 dict（引擎负责最终校验）。

    空串/纯空白 = 缺省（字段不入卡）；enum 存枚举值本身；pair 按逗号拆两数。
    转换失败抛 CardError（消息面向用户，交页签 notify 展示）。
    """
    card = {"category": MODULE_DEFAULTS[module_id]["category"],
            "pipe_spec": "48.3x3.6"}
    for path, label, kind, _unit, _opts in FIELD_SPECS[module_id]:
        text = (values.get(path) or "").strip()
        if text == "":
            continue
        if kind == "enum":
            value = text
        elif kind == "text":
            value = text
        elif kind == "int":
            value = _to_int(text, label)
        elif kind == "number":
            value = _to_float(text, label)
        elif kind == "pair":
            parts = [p.strip() for p in text.split(",")]
            if len(parts) != 2:
                raise CardError("%s 须为两个数值（逗号分隔），得到 %r" % (label, text))
            value = [_to_float(p, label) for p in parts]
        else:
            raise CardError("未知字段类型 %r（%s）" % (kind, label))
        node = card
        parts = path.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    if module_id in ("M-1", "M-3"):
        card["wind"] = "不组合"
    if module_id == "M-4":
        card["tie_type"] = "steel_pipe_coupler"
    return card


def _to_float(text, label):
    try:
        v = float(text)
    except ValueError:
        raise CardError("%s 须为数值，得到 %r" % (label, text))
    return v


def _to_int(text, label):
    try:
        v = int(text)
    except ValueError:
        try:
            fv = float(text)
        except ValueError:
            raise CardError("%s 须为整数，得到 %r" % (label, text))
        if fv != int(fv):
            raise CardError("%s 须为整数，得到 %r" % (label, text))
        v = int(fv)
    return v
