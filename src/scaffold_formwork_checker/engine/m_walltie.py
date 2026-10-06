# -*- coding: utf-8 -*-
"""M-4 连墙件验算（JGJ 130-2011 5.2.12~5.2.15）。

Nl=Nlw+N0（式5.2.12-3）；Nlw=1.4·wk·Aw（式5.2.13）；
强度 σ=Nl/Ac ≤ 0.85f 与稳定 Nl/(φA) ≤ 0.85f（式5.2.12-1/-2，双校核）；
钢管扣件连墙件须验算扣件抗滑 Nl ≤ Rc（5.2.15）。
Aw 按表6.4.2 连墙件布置最大间距：双排落地 3h×3la（≤40m²）、H>50m 2h×3la（≤27m²）、
单排 3h×3la（≤40m²）。
"""

import math

from . import scalars, tables
from .result import blocked_result, make_check, make_result

_CLAUSES_TIE = ("JGJ130-5.2.12", "JGJ130-5.2.13", "JGJ130-A.0.6", "JGJ130-5.1.6")
_CLAUSES_AW = ("JGJ130-6.4.2",)
_CLAUSES_ANTISLIP = ("JGJ130-5.2.15", "JGJ130-5.1.7")


def _fmt(x):
    return ("%.4f" % x).rstrip("0").rstrip(".")


def _coverage(kn, card, warnings):
    """单个连墙件覆盖迎风面积 Aw（表6.4.2）。返回 (aw_m2, 档位名)。"""
    spec = kn.threshold_value("T-JGJ130-walltie-spacing")
    rows = card["rows"]
    build_h = card.get("build_height_m")
    h, la = card["step_m"], card["long_spacing_m"]
    if rows == "double" and build_h is not None and build_h > 50.0:
        key = "双排悬挑_H>50m"
    elif rows == "double":
        key = "双排落地_H≤50m"
    else:
        key = "单排_H≤24m"
        if build_h is not None and build_h > 24.0:
            warnings.append("单排架搭设高度不应超过 24m（JGJ130-6.1.2），连墙件覆盖面积仍按表6.4.2 单排档计")
    entry = spec[key]
    cap = float(entry["每根覆盖面积_m2"])
    vertical = 3.0 if str(entry["竖向"]).strip().startswith("3") else 2.0
    horizontal = 3.0 if str(entry["水平"]).strip().startswith("3") else 2.0
    aw = vertical * h * horizontal * la
    if build_h is None:
        warnings.append("未提供 build_height_m，按 %s 档取 Aw=min(%s·h×%s·la, %s m²)"
                        % (key, _fmt(vertical), _fmt(horizontal), _fmt(cap)))
    return min(aw, cap), key


def _wk(card, kn, warnings):
    from .m_stability import _wk as _wk_impl
    return _wk_impl(card, kn, warnings)


def calc_m4(card, kn):
    unverified = kn.unverified("M-4")
    if unverified:
        return blocked_result("M-4", unverified)
    warnings = []
    aw, aw_key = _coverage(kn, card, warnings)
    wk, _ = _wk(card, kn, warnings)
    n0 = scalars.tie_n0(kn, card["rows"])
    nlw = 1.4 * wk * aw
    nl = nlw + n0
    # 连墙件杆件：两端铰接，λ=ceil(l0/i) 查表A.0.6（口径同决策 #18）
    _, _, _, i_mm = scalars.section_props(kn)
    a_mm2, _, _, _ = scalars.section_props(kn)
    l0_mm = card["tie_length_m"] * 1000.0
    lam = math.ceil(l0_mm / i_mm)
    phi = tables.phi_of(float(lam))
    f = scalars.steel_f_130(kn)
    f85 = 0.85 * f
    sigma_strength = nl * 1000.0 / a_mm2
    sigma_stab = nl * 1000.0 / (phi * a_mm2)
    rc = scalars.coupler_rc(kn)
    checks = [
        make_check(
            "tie_strength", "Nl/Ac ≤ 0.85f",
            "Nl=%s kN, Ac=%s mm² → σ=%s N/mm² ≤ 0.85f=%s N/mm²"
            % (_fmt(nl), _fmt(a_mm2), _fmt(sigma_strength), _fmt(f85)),
            sigma_strength / f85, f85, list(_CLAUSES_TIE)),
        make_check(
            "tie_stability", "Nl/(φA) ≤ 0.85f",
            "Nl=%s kN, φ=%s（λ=%d）, A=%s mm² → σ=%s N/mm² ≤ 0.85f=%s N/mm²"
            % (_fmt(nl), _fmt(phi), lam, _fmt(a_mm2), _fmt(sigma_stab), _fmt(f85)),
            sigma_stab / f85, f85, list(_CLAUSES_TIE)),
        make_check(
            "antislip", "Nl ≤ Rc",
            "Nl=%s kN ≤ Rc=%s kN（直角扣件抗滑，钢管扣件连墙件）" % (_fmt(nl), _fmt(rc)),
            nl / rc, rc, list(_CLAUSES_ANTISLIP)),
    ]
    detail = {
        "Aw_m2": aw, "Aw_rule": aw_key, "wk_kN_per_m2": wk, "Nlw_kN": nlw,
        "N0_kN": n0, "Nl_kN": nl, "l0_mm": l0_mm, "lambda": lam, "phi": phi,
        "sigma_strength_N_per_mm2": sigma_strength,
        "sigma_stab_N_per_mm2": sigma_stab, "f85_N_per_mm2": f85, "Rc_kN": rc,
    }
    return make_result("M-4", checks, detail, warnings)
