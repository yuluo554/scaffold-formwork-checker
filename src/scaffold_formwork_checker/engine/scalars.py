# -*- coding: utf-8 -*-
"""M2 标量取值助手：全部经条款库阈值表取用（status 硬拦截覆盖），不散落常数。

代码内仅保留 thresholds.json 无独立数值字段的三处结构量（tables.py）：
k=1.155（T-JGJ130-mu-coef verify 注）、E=206000（T-JGJ130-steel-design 条件注）、
JGJ162 立柱步距上限 1.8m（T-JGJ162-column-step）——均由测试与台账对账。
"""

from . import tables


def section_props(kn):
    """φ48.3×3.6 截面特性（T-JGJ130-section-props）：A/I/W/i。"""
    v = kn.threshold_value("T-JGJ130-section-props")
    return float(v["A_mm2"]), float(v["I_mm4"]), float(v["W_mm3"]), float(v["i_mm"])


def steel_f_130(kn):
    """Q235 钢强度设计值（JGJ130 表5.1.6）：205 N/mm²。"""
    return float(kn.threshold_value("T-JGJ130-steel-design"))


def steel_f_162(kn):
    """Q235 钢强度设计值（JGJ162 表A.1.1-1，t≤16mm）：215 N/mm²。"""
    return float(kn.threshold_value("T-JGJ162-steel-design"))


def coupler_rc(kn):
    """直角扣件抗滑承载力设计值（T-JGJ130-coupler-capacity）：8.0 kN。"""
    return float(kn.threshold_value("T-JGJ130-coupler-capacity")["直角扣件抗滑"])


def tie_n0(kn, rows):
    """连墙件约束平面外变形轴向力 N0（T-JGJ130-tie-N0）：单排 2.0 / 双排 3.0 kN。"""
    v = kn.threshold_value("T-JGJ130-tie-N0")
    return float(v["单排架" if rows == "single" else "双排架"])


def partial_factors_130(kn):
    """JGJ130 荷载分项系数（T-JGJ130-partial-factors）：永久 1.2 / 可变 1.4 / 挠度标准组合 1.0。"""
    v = kn.threshold_value("T-JGJ130-partial-factors")
    return float(v["永久荷载"]), float(v["可变荷载"]), float(v["挠度标准组合"])


def gamma0_162(kn):
    """JGJ162 结构重要性系数 γ0（T-JGJ162-partial-factors）：0.9。"""
    return float(kn.threshold_value("T-JGJ162-partial-factors")["结构重要性系数γ0"])


def steel_e():
    """钢材弹性模量（N/mm²）：2.06×10⁵（T-JGJ130-steel-design 条件注）。"""
    return tables.STEEL_E


def k_length_add():
    """立杆计算长度附加系数 k（JGJ130-5.2.8）：1.155。"""
    return tables.K_LENGTH_ADD


def m6_step_max():
    """JGJ162 扣件钢管立柱最大步距（T-JGJ162-column-step）：1.8 m。"""
    return tables.M6_STEP_MAX_M
