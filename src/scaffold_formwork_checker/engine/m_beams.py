# -*- coding: utf-8 -*-
"""M-3 纵/横向水平杆验算（JGJ 130-2011 5.2.1~5.2.5）。

横向水平杆（member=cross）：简支梁，计算跨度 l0=lb（图5.2.4 双排），负担宽度=la；
  M=qd·lb²/8；v=5·qk·l0⁴/(384EI)（标准组合 1.0）；[v]=min(l/150, 10mm)（表5.1.8）；
  R=q·lb/2（传给纵向水平杆，扣件抗滑 5.2.5）。
纵向水平杆（member=long）：三跨等跨连续梁、每跨跨中集中力 P（=横向水平杆反力，5.2.4）；
  弯矩系数：支座 -0.150P·la、边跨跨中 0.175P·la（三弯矩方程导出），取边跨跨中控制；
  内支座反力 R=1.15P（扣件抗滑 5.2.5）。
"""

from . import scalars
from .result import blocked_result, make_check, make_result

_CLAUSES_STRENGTH = ("JGJ130-5.2.1", "JGJ130-5.2.2", "JGJ130-5.1.6", "JGJ130-B.0.1")
_CLAUSES_DEFLECTION = ("JGJ130-5.2.3", "JGJ130-5.1.8", "JGJ130-5.1.3")
_CLAUSES_ANTISLIP = ("JGJ130-5.2.5", "JGJ130-5.1.7")


def _fmt(x):
    return ("%.4f" % x).rstrip("0").rstrip(".")


def _line_loads(card, kn):
    """标准/设计线荷载（负担宽度=la）。qd=1.2·板·la+1.4·活·la（式5.2.2）。"""
    loads = card["loads"]
    la = card["long_spacing_m"]
    board, live = loads["board_kN_per_m2"], loads["live_kN_per_m2"]
    gamma_g, gamma_q, _ = scalars.partial_factors_130(kn)
    qk = (board + live) * la
    qd = gamma_g * board * la + gamma_q * live * la
    return qk, qd


def _deflection_limit(kn, span_mm):
    """[v]=min(l/150, 10mm)（表5.1.8 脚手板及纵横水平杆档）。"""
    # 结构量出自 T-JGJ130-deflection-limits（"min(l/150, 10mm)"），机器形见本函数
    return min(span_mm / 150.0, 10.0)


def calc_m3(card, kn):
    unverified = kn.unverified("M-3")
    if unverified:
        return blocked_result("M-3", unverified)
    la, lb = card["long_spacing_m"], card["cross_spacing_m"]
    _, _, w_mm3, _ = scalars.section_props(kn)
    _, i_mm4, _, _ = scalars.section_props(kn)
    f = scalars.steel_f_130(kn)
    rc = scalars.coupler_rc(kn)
    qk, qd = _line_loads(card, kn)
    checks, detail = [], {"qk_kN_per_m": qk, "qd_kN_per_m": qd}
    warnings = []

    if card["member"] == "cross":
        span_mm = lb * 1000.0
        m_design = qd * (lb ** 2) / 8.0
        sigma = m_design * 1e6 / w_mm3
        checks.append(make_check(
            "bending_strength", "M/W ≤ f",
            "M=q·l²/8=%s kN·m, W=%s mm³ → σ=%s N/mm² ≤ f=%s N/mm²"
            % (_fmt(m_design), _fmt(w_mm3), _fmt(sigma), _fmt(f)),
            sigma / f, f, list(_CLAUSES_STRENGTH)))
        v = 5.0 * qk * (span_mm ** 4) / (384.0 * scalars.steel_e() * i_mm4)
        v_allow = _deflection_limit(kn, span_mm)
        checks.append(make_check(
            "deflection", "v ≤ [v]",
            "v=5qk·l⁴/(384EI)=%s mm ≤ [v]=min(l/150,10mm)=%s mm"
            % (_fmt(v), _fmt(v_allow)),
            v / v_allow, v_allow, list(_CLAUSES_DEFLECTION)))
        detail.update({"M_design_kNm": m_design, "sigma_N_per_mm2": sigma,
                       "v_mm": v, "v_allow_mm": v_allow})
        r_force = qd * lb / 2.0
    else:
        p_design = qd * lb / 2.0          # 横向水平杆反力 → 纵向水平杆跨中集中力
        m_design = 0.175 * p_design * la  # 边跨跨中（支座 -0.150P·la）
        sigma = m_design * 1e6 / w_mm3
        checks.append(make_check(
            "bending_strength", "M/W ≤ f",
            "M=0.175·P·la=%s kN·m（P=%s kN）, W=%s mm³ → σ=%s N/mm² ≤ f=%s N/mm²"
            % (_fmt(m_design), _fmt(p_design), _fmt(w_mm3), _fmt(sigma), _fmt(f)),
            sigma / f, f, list(_CLAUSES_STRENGTH)))
        detail.update({"P_design_kN": p_design, "M_design_kNm": m_design,
                       "sigma_N_per_mm2": sigma})
        r_force = 1.15 * p_design         # 内支座反力（立杆扣件处）

    checks.append(make_check(
        "antislip", "R ≤ Rc",
        "R=%s kN ≤ Rc=%s kN（直角扣件抗滑）" % (_fmt(r_force), _fmt(rc)),
        r_force / rc, rc, list(_CLAUSES_ANTISLIP)))
    detail.update({"R_kN": r_force, "Rc_kN": rc})
    return make_result("M-3", checks, detail, warnings)
