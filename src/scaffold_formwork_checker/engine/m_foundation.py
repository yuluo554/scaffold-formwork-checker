# -*- coding: utf-8 -*-
"""M-5 立杆地基承载力验算（JGJ 130-2011 5.5.1/5.5.2）。

pk=Nk/A ≤ fg（式5.5.1）；fg 取值（5.5.2）：回填土地基=勘察报告特征值×0.4、
天然地基按勘察报告（调整系数 1.0）。Nk 为上部传至基础顶面轴向力标准值：
卡上显式给出（foundation.nk_kN），或给全架体参数按标准组合（分项系数 1.0）现算。
"""

from .card import CardError
from .m_stability import _axial_forces
from .result import blocked_result, make_check, make_result

_CLAUSES_FOUNDATION = ("JGJ130-5.5.1", "JGJ130-5.5.2")


def _fmt(x):
    return ("%.4f" % x).rstrip("0").rstrip(".")


def calc_m5(card, kn):
    unverified = kn.unverified("M-5")
    if unverified:
        return blocked_result("M-5", unverified)
    foundation = card["foundation"]
    warnings = []
    if "nk_kN" in foundation:
        nk = foundation["nk_kN"]
    elif "n_design_kN" in foundation:
        # 仅设计值可用时按标准值≈设计值/1.285 反推不可靠，直接拒收并提示
        raise CardError("M-5 需要轴力标准值 foundation.nk_kN（JGJ130 5.5.1 用标准组合）；"
                        "如只有设计值请补标准值或提供架体参数现算")
    else:
        nk = _standard_combo_nk(card, kn, warnings)
    pad_l, pad_w = foundation["pad_m"]
    area = pad_l * pad_w
    fgk = foundation["fgk_kPa"]
    reduction = foundation["reduction"]
    fg = fgk * reduction
    pk = nk / area
    ratio = pk / fg
    check = make_check(
        "foundation_bearing", "pk=Nk/A ≤ fg",
        "Nk=%s kN, A=%s×%s=%s m² → pk=%s kPa ≤ fg=%s×%s=%s kPa"
        % (_fmt(nk), _fmt(pad_l), _fmt(pad_w), _fmt(area), _fmt(pk),
           _fmt(fgk), _fmt(reduction), _fmt(fg)),
        ratio, fg, list(_CLAUSES_FOUNDATION))
    detail = {"Nk_kN": nk, "A_m2": area, "pk_kPa": pk, "fg_kPa": fg,
              "fgk_kPa": fgk, "reduction": reduction}
    return make_result("M-5", [check], detail, warnings)


def _standard_combo_nk(card, kn, warnings):
    """架体参数现算：Nk=NG1k+NG2k+NQk（标准组合，分项系数 1.0，5.5.1）。"""
    if "build_height_m" not in card.data:
        raise CardError("M-5 现算轴力缺 build_height_m")
    _gk, ng1k, ng2k, nqk = _axial_forces(card, kn, warnings)
    return ng1k + ng2k + nqk
