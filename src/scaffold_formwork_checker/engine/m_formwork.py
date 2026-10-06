# -*- coding: utf-8 -*-
"""M-6 模板支架验算（JGJ 162-2008）：立柱稳定（5.2.5）与立柱底地基（5.2.6）。

立柱稳定·不组合风：N=γ0·(1.2·ΣNGik+1.4·ΣNQik)（4.3.1，γ0=0.9）；
  l0=最大步距（5.2.5-3，扣件钢管立柱按单杆轴心受压，无 μ/k）；σ=N/(φA) ≤ f=215。
立柱稳定·组合风（室外露天）：Mw=0.9²×1.4·wk·la·h²/10（式5.2.5-15）；
  NQik 另加 Mw/lb（5.2.5-3）；Nw=γ0·(1.2·ΣNGik+0.9×1.4·ΣNQik)（式5.2.5-14）；
  σ=Nw/(φA)+Mw/W ≤ f。
立柱底地基：p=N/A ≤ mf·fak（5.2.6，mf=表5.2.6 折减系数）。
口径：φ 查表A.0.6（=JGJ162 附录D，同源同值）；f=215（表A.1.1-1，不得用 JGJ130 的 205）。
"""

import math

from . import scalars, tables
from .card import CardError
from .m_stability import _mu_s
from .result import blocked_result, make_check, make_result

_CLAUSES_COLUMN = ("JGJ162-5.2.5", "JGJ162-4.3.1", "JGJ162-4.2.3", "JGJ130-A.0.6", "JGJ162-A.1.1-1")
_CLAUSES_FOUNDATION = ("JGJ162-5.2.6",)


def _fmt(x):
    return ("%.4f" % x).rstrip("0").rstrip(".")


def _wk_direct(card, kn, warnings):
    """M-6 风荷载标准值：卡上 wk 直给，或 w0·μz·μs 合成（βz=1，n=10 年，162 4.1.3）。"""
    wind = card["wind"]
    if "wk_kN_per_m2" in wind:
        return float(wind["wk_kN_per_m2"])
    w0 = wind["w0_kN_per_m2"]
    mu_z = wind["mu_z"]
    mu_s = _mu_s(wind, card, warnings)
    return mu_z * mu_s * w0


def calc_m6_column(card, kn):
    unverified = kn.unverified("M-6")
    if unverified:
        return blocked_result("M-6", unverified)
    warnings = []
    step = card["step_m"]
    if step > scalars.m6_step_max() + 1e-9:
        warnings.append(
            "步距 %s m 超过 JGJ162-5.2.5 扣件钢管立柱最大步距 1.8m（T-JGJ162-column-step），"
            "计算仍按输入步距进行，构造整改见核查模块" % _fmt(step))
    la, lb = card["pole_spacing_m"]
    loads = card["loads"]
    slab = card["slab_thickness_m"]
    g1k = loads["g1k_kN_per_m2"]
    g2k = loads["concrete_kN_per_m3"] * slab          # 新浇混凝土自重×板厚
    g3k = loads["rebar_kN_per_m3_slab"] * slab        # 钢筋自重×板厚
    ng = (g1k + g2k + g3k) * la * lb                  # 立杆负荷面积内恒载标准值
    q1k = loads["q1k_kN_per_m2"]
    gamma0 = scalars.gamma0_162(kn)
    a_mm2, _, w_mm3, i_mm = scalars.section_props(kn)
    f = scalars.steel_f_162(kn)
    l0_mm = step * 1000.0
    lam = math.ceil(l0_mm / i_mm)
    phi = tables.phi_of(float(lam))

    if card["wind"] == "不组合":
        n = gamma0 * (1.2 * ng + 1.4 * q1k * la * lb)
        sigma = n * 1000.0 / (phi * a_mm2)
        expr = "N/(φA) ≤ f"
        substituted = ("N=%s kN（γ0=%s）, φ=%s（λ=%d）, A=%s mm² → σ=%s N/mm² ≤ f=%s N/mm²"
                       % (_fmt(n), _fmt(gamma0), _fmt(phi), lam, _fmt(a_mm2),
                          _fmt(sigma), _fmt(f)))
        detail = {"NG_kN": ng, "N_design_kN": n, "l0_mm": l0_mm, "lambda": lam,
                  "phi": phi, "sigma_N_per_mm2": sigma, "f": f}
    else:
        wk = _wk_direct(card, kn, warnings)
        mwk = wk * la * (step ** 2) / 10.0
        mw = 0.9 ** 2 * 1.4 * mwk                    # 式5.2.5-15
        nqik = q1k * la * lb + mw / lb               # 另加 Mw/lb（5.2.5-3）
        nw = gamma0 * (1.2 * ng + 0.9 * 1.4 * nqik)  # 式5.2.5-14
        sigma = nw * 1000.0 / (phi * a_mm2) + mw * 1e6 / w_mm3
        expr = "Nw/(φA) + Mw/W ≤ f"
        substituted = ("Nw=%s kN（γ0=%s）, φ=%s（λ=%d）, A=%s mm², Mw=%s kN·m, W=%s mm³"
                       " → σ=%s N/mm² ≤ f=%s N/mm²"
                       % (_fmt(nw), _fmt(gamma0), _fmt(phi), lam, _fmt(a_mm2),
                          _fmt(mw), _fmt(w_mm3), _fmt(sigma), _fmt(f)))
        detail = {"NG_kN": ng, "wk_kN_per_m2": wk, "Mwk_kNm": mwk, "Mw_kNm": mw,
                  "NQik_kN": nqik, "Nw_kN": nw, "l0_mm": l0_mm, "lambda": lam,
                  "phi": phi, "sigma_N_per_mm2": sigma, "f": f}
        n = nw
    check = make_check("column_stability", expr, substituted, sigma / f, f,
                       list(_CLAUSES_COLUMN))
    return make_result("M-6", [check], detail, warnings)


def calc_m6_foundation(card, kn):
    unverified = kn.unverified("M-6")
    if unverified:
        return blocked_result("M-6", unverified)
    foundation = card["foundation"]
    n = foundation.get("n_design_kN")
    if n is None:
        raise CardError("M-6 立柱地基需要轴向力设计值 foundation.n_design_kN（5.2.6 用设计值）")
    pad_l, pad_w = foundation["pad_m"]
    area = pad_l * pad_w
    mf = foundation["mf"]
    fak = foundation["fak_kPa"]
    p = n / area
    limit = mf * fak
    ratio = p / limit
    check = make_check(
        "foundation_bearing", "p=N/A ≤ mf·fak",
        "N=%s kN, A=%s×%s=%s m² → p=%s kPa ≤ mf·fak=%s×%s=%s kPa"
        % (_fmt(n), _fmt(pad_l), _fmt(pad_w), _fmt(area), _fmt(p),
           _fmt(mf), _fmt(fak), _fmt(limit)),
        ratio, limit, list(_CLAUSES_FOUNDATION))
    detail = {"N_kN": n, "A_m2": area, "p_kPa": p, "mf": mf, "fak_kPa": fak}
    return make_result("M-6", [check], detail, [])


def calc_m6(card, kn):
    """M-6 入口：按参数卡内容分派立柱稳定（含风两工况）或立柱底地基。"""
    if "foundation" in card:
        return calc_m6_foundation(card, kn)
    return calc_m6_column(card, kn)
