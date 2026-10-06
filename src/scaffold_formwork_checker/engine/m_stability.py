# -*- coding: utf-8 -*-
"""M-1/M-2 立杆稳定性验算（JGJ 130-2011 5.2.6~5.2.9）。

M-1 不组合风：N=1.2(NG1k+NG2k)+1.4ΣNQk（式5.2.7-1）；σ=N/(φA) ≤ f
M-2 组合风：  N=1.2(NG1k+NG2k)+0.9×1.4ΣNQk（式5.2.7-2）；
              Mw=0.9×1.4·wk·la·h²/10（式5.2.9）；σ=N/(φA)+Mw/W ≤ f
口径：λ=ceil(l0/i) 查表A.0.6 离散档（决策 #18，禁插值）；l0=k·μ·h（式5.2.8）。
"""

from . import scalars, tables
from .card import CardError
from .result import blocked_result, make_check, make_result

_CLAUSES_STAB = ("JGJ130-5.2.6", "JGJ130-5.2.7", "JGJ130-5.2.8", "JGJ130-A.0.6",
                 "JGJ130-5.1.6", "JGJ130-B.0.1")
_CLAUSES_WIND = ("JGJ130-4.2.5", "JGJ130-4.2.6")


def _mu_s(wind, card, warnings):
    """风荷载体型系数 μs（表4.2.6 / 4.2.7 / 表A.0.5）。"""
    if "shape_mu_s" in wind:
        return float(wind["shape_mu_s"])
    state = wind.get("scaffold_state", "enclosed_net")
    back_wall = wind.get("back_wall") or "全封闭墙"
    if "shape_phi" in wind:
        shape_phi = float(wind["shape_phi"])
    elif state == "open":
        # 敞开式：表A.0.5 按（步距,纵距）查挡风系数
        shape_phi = tables.wind_phi_a05_of(card["step_m"], card["long_spacing_m"])
    else:
        raise CardError("wind.shape_phi 缺失且无法由表A.0.5 查取（scaffold_state=%s）" % state)
    if state == "open":
        mu_s = 1.3 * shape_phi
    elif state in ("enclosed_net", "semi_enclosed") and back_wall == "全封闭墙":
        mu_s = 1.0 * shape_phi
        if state == "enclosed_net" and shape_phi < 0.8:
            warnings.append("密目式安全立网全封闭脚手架挡风系数 φ 不宜小于 0.8（JGJ130-4.2.7）")
    elif back_wall in ("敞开框架开洞墙", "敞开框架、开洞墙"):
        mu_s = 1.3 * shape_phi
    else:
        raise CardError("未支持的背靠墙面情形 %r（暂支持 全封闭墙/敞开框架开洞墙）" % (back_wall,))
    return mu_s


def _wk(card, kn, warnings):
    """风荷载标准值 wk=μz·μs·w0（式4.2.5）；卡上直接给 wk 时径用。"""
    wind = card["wind"]
    if "wk_kN_per_m2" in wind:
        return float(wind["wk_kN_per_m2"]), "输入值"
    w0 = wind["w0_kN_per_m2"]
    mu_z = wind["mu_z"]
    mu_s = _mu_s(wind, card, warnings)
    return mu_z * mu_s * w0, "μz·μs·w0（μs=%s）" % _fmt(mu_s)


def _fmt(x):
    return ("%.4f" % x).rstrip("0").rstrip(".")


def _axial_forces(card, kn, warnings):
    """立杆段轴力标准值三兄弟：NG1k（结构自重）/NG2k（构配件）/NQk（施工）。

    负担模型（算例真值库钉死，plan/05 §3 / HANDOFF-M2 口径 11）：
    脚手板每层负担面积=la×lb/2（内外立杆各半）；栏杆道数=脚手板层数（线荷载×la）；
    安全网 0.01 量级按输入值×la×H（外立面全高）。
    """
    loads = card["loads"]
    h, la, lb, build_h = card["step_m"], card["long_spacing_m"], card["cross_spacing_m"], card["build_height_m"]
    gk = loads["gk_struct_kN_per_m"]
    if gk is None:
        gk = tables.gk_of(h, la, card["rows"])
        warnings.append("未提供 loads.gk_struct_kN_per_m，已按表A.0.1 查取（h=%s, la=%s, %s 排）"
                        % (_fmt(h), _fmt(la), card["rows"]))
    ng1k = gk * build_h
    area_per = la * lb / 2.0
    ng2k = (loads["board_kN_per_m2"] * loads["board_layers"] * area_per
            + loads["rail_kN_per_m"] * loads["board_layers"] * la
            + loads["safety_net_kN_per_m2"] * la * build_h)
    nqk = loads["live_kN_per_m2"] * area_per
    return gk, ng1k, ng2k, nqk


def _slenderness(card, kn):
    """l0=k·μ·h（式5.2.8）→ λ=l0/i。返回 (mu, l0_mm, lam)。"""
    mu = tables.mu_of(card["rows"], card["wall_tie"], card["cross_spacing_m"])
    l0_mm = scalars.k_length_add() * mu * card["step_m"] * 1000.0
    _, _, _, i_mm = scalars.section_props(kn)
    return mu, l0_mm, l0_mm / i_mm


def calc_m1(card, kn):
    unverified = kn.unverified("M-1")
    if unverified:
        return blocked_result("M-1", unverified)
    warnings = []
    gk, ng1k, ng2k, nqk = _axial_forces(card, kn, warnings)
    gamma_g, gamma_q, _ = scalars.partial_factors_130(kn)
    n_design = gamma_g * (ng1k + ng2k) + gamma_q * nqk
    mu, l0_mm, lam = _slenderness(card, kn)
    phi = tables.phi_of(lam)
    a_mm2, _, w_mm3, _ = scalars.section_props(kn)
    f = scalars.steel_f_130(kn)
    sigma = n_design * 1000.0 / (phi * a_mm2)
    ratio = sigma / f
    check = make_check(
        "lizhigan_stability",
        "N/(φA) ≤ f",
        "N=%s kN, φ=%s, A=%s mm² → σ=%s N/mm² ≤ f=%s N/mm²"
        % (_fmt(n_design), _fmt(phi), _fmt(a_mm2), _fmt(sigma), _fmt(f)),
        ratio, f, list(_CLAUSES_STAB))
    detail = {
        "gk_kN_per_m": gk, "NG1k_kN": ng1k, "NG2k_kN": ng2k, "NQk_kN": nqk,
        "N_design_kN": n_design, "mu": mu, "l0_mm": l0_mm, "lambda": lam,
        "phi": phi, "sigma_N_per_mm2": sigma, "f": f,
    }
    return make_result("M-1", [check], detail, warnings)


def calc_m2(card, kn):
    unverified = kn.unverified("M-2")
    if unverified:
        return blocked_result("M-2", unverified)
    warnings = []
    gk, ng1k, ng2k, nqk = _axial_forces(card, kn, warnings)
    gamma_g, gamma_q, _ = scalars.partial_factors_130(kn)
    wk, wk_note = _wk(card, kn, warnings)
    n_design = gamma_g * (ng1k + ng2k) + 0.9 * gamma_q * nqk   # 式5.2.7-2（0.9 组合系数在公式内）
    h, la = card["step_m"], card["long_spacing_m"]
    mwk = wk * la * (h ** 2) / 10.0                            # 式5.2.9 中段，kN·m
    mw = 0.9 * 1.4 * mwk                                       # 式5.2.9 设计值
    mu, l0_mm, lam = _slenderness(card, kn)
    phi = tables.phi_of(lam)
    a_mm2, _, w_mm3, _ = scalars.section_props(kn)
    f = scalars.steel_f_130(kn)
    sigma_axial = n_design * 1000.0 / (phi * a_mm2)
    sigma_bend = mw * 1e6 / w_mm3
    sigma = sigma_axial + sigma_bend
    ratio = sigma / f
    check = make_check(
        "lizhigan_stability",
        "N/(φA) + Mw/W ≤ f",
        "N=%s kN, φ=%s, A=%s mm², Mw=%s kN·m, W=%s mm³ → σ=%s N/mm² ≤ f=%s N/mm²"
        % (_fmt(n_design), _fmt(phi), _fmt(a_mm2), _fmt(mw), _fmt(w_mm3), _fmt(sigma), _fmt(f)),
        ratio, f, list(_CLAUSES_STAB) + list(_CLAUSES_WIND))
    detail = {
        "gk_kN_per_m": gk, "NG1k_kN": ng1k, "NG2k_kN": ng2k, "NQk_kN": nqk,
        "wk_kN_per_m2": wk, "N_design_kN": n_design, "Mwk_kNm": mwk, "Mw_kNm": mw,
        "mu": mu, "l0_mm": l0_mm, "lambda": lam, "phi": phi,
        "sigma_bend_N_per_mm2": sigma_bend, "sigma_N_per_mm2": sigma, "f": f,
    }
    return make_result("M-2", [check], detail, warnings)
