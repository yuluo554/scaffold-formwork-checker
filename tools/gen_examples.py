# -*- coding: utf-8 -*-
"""M1-4 算例真值库生成与复算脚本（tools/gen_examples.py）。

用途：
1. 按 data/knowledge/clauses/（formulas.json + thresholds.json，status=已核对）构造
   13 个规范条文算例，覆盖 M-1/M-2/M-3/M-4/M-5/M-6 与不合格路径；
2. 每个算例全部中间量由本脚本按条款库数值现场计算并断言（防手算错）；
3. 输出 data/examples/*.json（UTF-8 无 BOM，LF，无时间戳，字节确定）。

复算口径（引擎 M2 必须一致，改口径=改真值，须重跑本脚本并整目录提交）：
- λ 查表档位：ceil(l0/i) 向上取整（偏安全）；表 A.0.6 离散档查表，禁止线性插值；
- 荷载分项系数 JGJ130：1.2/1.4（挠度标准组合 1.0）；JGJ162：γ0=0.9 外包；
- 脚手板/栏杆/安全网负担模型：见各算例 input_card.model_notes（钉死）；
- 纵向水平杆模型：三跨等跨连续梁、每跨跨中集中力 P——支座弯矩 -0.150P·la、
  边跨跨中 0.175P·la（三弯矩方程导出）、内支座反力 1.15P；
- 横向水平杆模型：简支梁，跨度 l0=lb（图5.2.4 双排），承受均布 q（负担宽度=la）。

M2 起：φ/gk 数值矩阵与 phi_of 复用 engine.tables（单一事实源，转录版完整 251 档）；
input_card 含引擎路由字段（rows/member/tie 轴力显式值），数值期望不受影响。

用法: py -X utf8 tools/gen_examples.py [--check]
  --check: 只复算断言，不写文件（守门测试用）
"""
import json
import math
import os
import sys

from scaffold_formwork_checker.engine import tables

# ---- 已核对常数（thresholds.json）----
A_MM2 = 506.0        # T-JGJ130-section-props（48.3x3.6）
I_MM4 = 127100.0
W_MM3 = 5260.0
I_MM = 15.9
F130 = 205.0         # T-JGJ130-steel-design
F162 = 215.0         # T-JGJ162-steel-design
E_STEEL = 206000.0   # N/mm²（表5.1.6 / JGJ162 表A.1.3）
K_ADD = 1.155        # JGJ130-5.2.8

# 表A.0.6 完整 251 档（M2 引擎转录版，原 M1 锚点集为其子集）
PHI = tables.PHI_TABLE

# 表A.0.1 gk（kN/m，双排）：步距h -> 纵距la -> gk（原文表图转录，M2 引擎同源）
GK_2PAI = tables.GK_TABLE["double"]

SOURCE_130 = {
    "type": "规范条文算例",
    "standard": "JGJ 130-2011",
    "basis": "data/knowledge/clauses/{jgj130_clauses,formulas,thresholds}.json（status=已核对）",
    "recalc_tool": "tools/gen_examples.py",
    "fetched": "2026-10-06",
}
SOURCE_162 = {
    "type": "规范条文算例",
    "standard": "JGJ 162-2008",
    "basis": "data/knowledge/clauses/{jgj162_clauses,formulas,thresholds}.json（status=已核对）",
    "recalc_tool": "tools/gen_examples.py",
    "fetched": "2026-10-06",
}


def phi_of(lam):
    """λ 向上取整查表A.0.6（本脚本只需已转录档）。"""
    key = int(math.ceil(lam))
    if key not in PHI:
        raise AssertionError("λ=%s→档 %d 未在已转录锚点内，请先补充表A.0.6该行转录" % (lam, key))
    return PHI[key]


def r4(x):
    return round(x + 0.0, 4)


def example_lizhigan_nw_001():
    """M-1 立杆稳定·不组合风（h1.8/la1.5/lb1.05/二步三跨/H12m/装修2.0）。"""
    h, la, lb, H = 1.8, 1.5, 1.05, 12.0
    mu = 1.50                      # 表5.2.8 双排二步三跨 lb=1.05
    gk = GK_2PAI[1.80][1.5]        # 0.1295
    board_l, board_n = 0.30, 2     # 冲压钢脚手板 kN/m² × 层数
    rail, net = 0.16, 0.01         # 栏杆挡脚板 kN/m、安全网 kN/m²
    q_live = 2.0                   # 装修作业层
    ng1k = gk * H
    area_per = la * lb / 2.0       # 内（外）立杆负担面积
    ng2k = board_l * board_n * area_per + rail * board_n * la + net * la * H
    nqk = q_live * area_per
    n_design = 1.2 * (ng1k + ng2k) + 1.4 * nqk          # kN（式5.2.7-1）
    l0 = K_ADD * mu * h * 1000.0
    lam = l0 / I_MM
    phi = phi_of(lam)
    sigma = n_design * 1000.0 / (phi * A_MM2)
    ratio = sigma / F130
    assert abs(ng1k - 1.554) < 1e-9, ng1k
    assert abs(ng2k - 1.1325) < 1e-9, ng2k
    assert abs(n_design - 5.4288) < 1e-9, n_design
    assert abs(lam - 196.132) < 0.01, lam
    assert abs(sigma - 57.6820) < 0.01, sigma
    return {
        "example_id": "EX-lizhigan-nw-001",
        "title": "立杆稳定性（不组合风）落地双排装修架",
        "module": "M-1",
        "source": SOURCE_130,
        "input_card": {
            "category": "coupler_steel_pipe_scaffold", "rows": "double",
            "build_height_m": H, "step_m": h, "long_spacing_m": la,
            "cross_spacing_m": lb, "wall_tie": "two_step_three_span",
            "pipe_spec": "48.3x3.6", "steel_grade": "Q235A",
            "wind": "不组合",
            "loads": {
                "gk_struct_kN_per_m": gk, "board_kN_per_m2": board_l,
                "board_layers": board_n, "rail_kN_per_m": rail,
                "safety_net_kN_per_m2": net, "live_kN_per_m2": q_live
            },
            "model_notes": [
                "脚手板每层负担面积=la×lb/2（内外立杆各半）",
                "栏杆挡脚板道数=脚手板层数，线荷载×la",
                "安全网 0.01 kN/m² × la × H（外立面全高）",
                "μ=1.50（表5.2.8 二步三跨 lb=1.05）；λ=ceil(l0/i) 查表A.0.6"
            ]
        },
        "expect": {
            "checks": [{"item": "lizhigan_stability", "ratio": r4(ratio), "tolerance": 0.01, "verdict": "pass"}],
            "intermediate": {
                "NG1k_kN": r4(ng1k), "NG2k_kN": r4(ng2k), "NQk_kN": r4(nqk),
                "N_design_kN": r4(n_design), "l0_mm": r4(l0), "lambda": r4(lam),
                "phi": phi, "sigma_N_per_mm2": r4(sigma), "f": F130
            }
        }
    }


def example_lizhigan_w_001():
    """M-2 立杆稳定·组合风（密目网全封闭背靠全封闭墙）。"""
    h, la, lb, H = 1.8, 1.5, 1.05, 12.0
    mu = 1.50
    gk = GK_2PAI[1.80][1.5]
    board_l, board_n, rail, net = 0.30, 2, 0.16, 0.01
    q_live = 2.0
    w0, muz, shape_phi = 0.4, 1.0, 0.8   # 密目网全封闭挡风系数取 0.8（4.2.7），背靠全封闭墙 μs=1.0φ
    ng1k = gk * H
    area_per = la * lb / 2.0
    ng2k = board_l * board_n * area_per + rail * board_n * la + net * la * H
    nqk = q_live * area_per
    wk = muz * 1.0 * shape_phi * w0      # μs=1.0φ（表4.2.6）
    n_design = 1.2 * (ng1k + ng2k) + 0.9 * 1.4 * nqk    # 式5.2.7-2
    mwk = wk * la * (h ** 2) / 10.0      # kN·m（式5.2.9 中段）
    mw = 0.9 * 1.4 * mwk                 # kN·m
    l0 = K_ADD * mu * h * 1000.0
    lam = l0 / I_MM
    phi = phi_of(lam)
    sigma = n_design * 1000.0 / (phi * A_MM2) + (mw * 1e6) / W_MM3
    ratio = sigma / F130
    assert abs(wk - 0.32) < 1e-12, wk
    assert abs(n_design - 5.2083) < 1e-9, n_design
    assert abs(mw - 0.1959552) < 1e-6, mw
    assert abs(sigma - 92.5930) < 0.01, sigma
    return {
        "example_id": "EX-lizhigan-w-001",
        "title": "立杆稳定性（组合风）密目网全封闭双排装修架",
        "module": "M-2",
        "source": SOURCE_130,
        "input_card": {
            "category": "coupler_steel_pipe_scaffold", "rows": "double",
            "build_height_m": H, "step_m": h, "long_spacing_m": la,
            "cross_spacing_m": lb, "wall_tie": "two_step_three_span",
            "pipe_spec": "48.3x3.6", "steel_grade": "Q235A",
            "wind": {"w0_kN_per_m2": w0, "mu_z": muz,
                     "scaffold_state": "enclosed_net", "shape_phi": shape_phi,
                     "back_wall": "全封闭墙"},
            "loads": {
                "gk_struct_kN_per_m": gk, "board_kN_per_m2": board_l,
                "board_layers": board_n, "rail_kN_per_m": rail,
                "safety_net_kN_per_m2": net, "live_kN_per_m2": q_live
            },
            "model_notes": [
                "μs=1.0φ（表4.2.6 全封闭/半封闭、背靠全封闭墙），φ=0.8（4.2.7 密目网全封闭下限）",
                "组合风轴力用式5.2.7-2（0.9×1.4 施工项）；Mw=0.9×1.4·wk·la·h²/10"
            ]
        },
        "expect": {
            "checks": [{"item": "lizhigan_stability", "ratio": r4(ratio), "tolerance": 0.01, "verdict": "pass"}],
            "intermediate": {
                "wk_kN_per_m2": r4(wk), "N_design_kN": r4(n_design),
                "Mwk_kNm": r4(mwk), "Mw_kNm": r4(mw), "lambda": r4(lam),
                "phi": phi, "sigma_bend_N_per_mm2": r4((mw * 1e6) / W_MM3),
                "sigma_N_per_mm2": r4(sigma), "f": F130
            }
        }
    }


def example_lizhigan_w_002():
    """M-2 变体：敞开式脚手架 μs=1.3φ（表4.2.6），φ 查表A.0.5。"""
    base = example_lizhigan_nw_001()
    w0, muz, shape_phi_a05 = 0.4, 1.0, 0.090   # 表A.0.5 步距1.80/纵距1.50 → 0.090
    nqk = 1.575
    ng_sum = 1.554 + 1.1325
    wk = muz * 1.3 * shape_phi_a05 * w0        # μs=1.3φ（敞开、背靠敞开框架开洞墙按 1.3φ 档）
    n_design = 1.2 * ng_sum + 0.9 * 1.4 * nqk
    mwk = wk * 1.5 * (1.8 ** 2) / 10.0
    mw = 0.9 * 1.4 * mwk
    l0 = K_ADD * 1.50 * 1.8 * 1000.0
    lam = l0 / I_MM                 # 196.13（与 EX-lizhigan-nw-001 同几何同 λ；M2 修正：原记录误写档位号 197.0）
    phi = phi_of(lam)               # ceil → 197 档 → 0.186
    sigma = n_design * 1000.0 / (phi * A_MM2) + (mw * 1e6) / W_MM3
    ratio = sigma / F130
    assert abs(wk - 0.0468) < 1e-12, wk
    assert abs(sigma - 60.7863) < 0.02, sigma
    return {
        "example_id": "EX-lizhigan-w-002",
        "title": "立杆稳定性（组合风）敞开式双排脚手架",
        "module": "M-2",
        "source": SOURCE_130,
        "input_card": dict(base["input_card"], wind={
            "w0_kN_per_m2": w0, "mu_z": muz, "scaffold_state": "open",
            "shape_phi_from_A05": shape_phi_a05, "shape_mu_s": 1.3 * shape_phi_a05,
            "back_wall": "敞开框架开洞墙"}),
        "expect": {
            "checks": [{"item": "lizhigan_stability", "ratio": r4(ratio), "tolerance": 0.01, "verdict": "pass"}],
            "intermediate": {
                "wk_kN_per_m2": r4(wk), "N_design_kN": r4(n_design),
                "Mw_kNm": r4(mw), "lambda": lam, "phi": phi,
                "sigma_N_per_mm2": r4(sigma), "f": F130
            }
        }
    }


def example_lizhigan_nw_003_fail():
    """M-1 不合格路径：应力比>1。"""
    h, la, lb, H = 1.8, 1.8, 1.55, 24.0
    mu = 1.80                      # 表5.2.8 双排三步三跨 lb=1.55
    gk = GK_2PAI[1.80][1.8]        # 0.1389
    board_l, board_n = 0.30, 4
    rail, net = 0.16, 0.01
    q_live = 3.0                   # 混凝土/砌筑结构
    ng1k = gk * H
    area_per = la * lb / 2.0
    ng2k = board_l * board_n * area_per + rail * board_n * la + net * la * H
    nqk = q_live * area_per
    n_design = 1.2 * (ng1k + ng2k) + 1.4 * nqk
    l0 = K_ADD * mu * h * 1000.0
    lam = l0 / I_MM
    phi = phi_of(lam)              # 235.36 → 236 → 0.131
    sigma = n_design * 1000.0 / (phi * A_MM2)
    ratio = sigma / F130
    assert abs(ng1k - 3.3336) < 1e-9, ng1k
    assert abs(n_design - 13.76892) < 1e-9, n_design
    assert abs(sigma - 207.7136) < 0.01, sigma
    assert ratio > 1.0
    return {
        "example_id": "EX-lizhigan-nw-003",
        "title": "立杆稳定性（不组合风）超载不合格例",
        "module": "M-1",
        "source": SOURCE_130,
        "input_card": {
            "category": "coupler_steel_pipe_scaffold", "rows": "double",
            "build_height_m": H, "step_m": h, "long_spacing_m": la,
            "cross_spacing_m": lb, "wall_tie": "three_step_three_span",
            "pipe_spec": "48.3x3.6", "steel_grade": "Q235A", "wind": "不组合",
            "loads": {
                "gk_struct_kN_per_m": gk, "board_kN_per_m2": board_l,
                "board_layers": board_n, "rail_kN_per_m": rail,
                "safety_net_kN_per_m2": net, "live_kN_per_m2": q_live
            },
            "model_notes": ["同 EX-lizhigan-nw-001 负担模型；μ=1.80（表5.2.8 三步三跨 lb=1.55）",
                            "本例设计为应力比>1 的不合格路径（σ>f）"]
        },
        "expect": {
            "checks": [{"item": "lizhigan_stability", "ratio": r4(ratio), "tolerance": 0.01, "verdict": "fail"}],
            "intermediate": {
                "NG1k_kN": r4(ng1k), "NG2k_kN": r4(ng2k), "NQk_kN": r4(nqk),
                "N_design_kN": r4(n_design), "lambda": r4(lam), "phi": phi,
                "sigma_N_per_mm2": r4(sigma), "f": F130
            }
        }
    }


def example_lizhigan_nw_002():
    """M-1 变体：h1.5/la1.8/lb1.30/三步三跨/H18m/施工3.0。"""
    h, la, lb, H = 1.5, 1.8, 1.30, 18.0
    mu = 1.75                      # 表5.2.8 双排三步三跨 lb=1.30
    gk = GK_2PAI[1.50][1.8]        # 0.1552
    board_l, board_n = 0.30, 2
    rail, net = 0.16, 0.01
    q_live = 3.0
    ng1k = gk * H
    area_per = la * lb / 2.0
    ng2k = board_l * board_n * area_per + rail * board_n * la + net * la * H
    nqk = q_live * area_per
    n_design = 1.2 * (ng1k + ng2k) + 1.4 * nqk
    l0 = K_ADD * mu * h * 1000.0
    lam = l0 / I_MM
    phi = phi_of(lam)              # 190.69 → 191 → 0.197
    sigma = n_design * 1000.0 / (phi * A_MM2)
    ratio = sigma / F130
    assert abs(ng1k - 2.7936) < 1e-9, ng1k
    assert abs(n_design - 10.18872) < 1e-9, n_design
    assert abs(sigma - 102.2123) < 0.01, sigma
    return {
        "example_id": "EX-lizhigan-nw-002",
        "title": "立杆稳定性（不组合风）结构施工架（三步三跨）",
        "module": "M-1",
        "source": SOURCE_130,
        "input_card": {
            "category": "coupler_steel_pipe_scaffold", "rows": "double",
            "build_height_m": H, "step_m": h, "long_spacing_m": la,
            "cross_spacing_m": lb, "wall_tie": "three_step_three_span",
            "pipe_spec": "48.3x3.6", "steel_grade": "Q235A", "wind": "不组合",
            "loads": {
                "gk_struct_kN_per_m": gk, "board_kN_per_m2": board_l,
                "board_layers": board_n, "rail_kN_per_m": rail,
                "safety_net_kN_per_m2": net, "live_kN_per_m2": q_live
            },
            "model_notes": ["同 EX-lizhigan-nw-001 负担模型；μ=1.75（表5.2.8 三步三跨 lb=1.30）"]
        },
        "expect": {
            "checks": [{"item": "lizhigan_stability", "ratio": r4(ratio), "tolerance": 0.01, "verdict": "pass"}],
            "intermediate": {
                "NG1k_kN": r4(ng1k), "NG2k_kN": r4(ng2k), "NQk_kN": r4(nqk),
                "N_design_kN": r4(n_design), "lambda": r4(lam), "phi": phi,
                "sigma_N_per_mm2": r4(sigma), "f": F130
            }
        }
    }


def example_henggan_001():
    """M-3 横向水平杆（简支梁，跨度 lb）：抗弯+挠度+扣件抗滑。"""
    la, lb = 1.5, 1.05
    board_l, q_live = 0.30, 2.0
    qk = (board_l + q_live) * la            # 标准线荷载（负担宽度 la）
    qd = 1.2 * board_l * la + 1.4 * q_live * la
    m_design = qd * (lb ** 2) / 8.0          # kN·m
    sigma = m_design * 1e6 / W_MM3
    v = 5.0 * qk * (lb * 1000.0) ** 4 / (384.0 * E_STEEL * I_MM4)   # mm（标准组合 1.0）
    v_allow = min(lb * 1000.0 / 150.0, 10.0)
    r_antislip = qd * lb / 2.0               # 横杆传给纵杆（直角扣件）
    assert abs(qd - 4.74) < 1e-9, qd
    assert abs(m_design - 0.65323125) < 1e-7, m_design
    assert abs(sigma - 124.1873) < 0.01, sigma
    assert abs(v - 2.0857) < 0.001, v
    return {
        "example_id": "EX-shuipinggan-hx-001",
        "title": "横向水平杆抗弯强度与挠度（简支梁）",
        "module": "M-3",
        "source": SOURCE_130,
        "input_card": {
            "category": "coupler_steel_pipe_scaffold", "rows": "double",
            "member": "cross",
            "step_m": 1.8, "long_spacing_m": la, "cross_spacing_m": lb,
            "pipe_spec": "48.3x3.6", "steel_grade": "Q235A",
            "loads": {"board_kN_per_m2": board_l, "live_kN_per_m2": q_live},
            "model_notes": [
                "简支梁，计算跨度 l0=lb（图5.2.4 双排）",
                "均布线荷载负担宽度=la（小横杆间距）",
                "挠度按标准组合（分项系数 1.0，5.1.3）；[v]=min(l/150,10mm)（表5.1.8）",
                "R=q·lb/2 为横杆传给纵向水平杆的作用力（5.2.5 抗滑）"
            ]
        },
        "expect": {
            "checks": [
                {"item": "bending_strength", "ratio": r4(sigma / F130), "tolerance": 0.01, "verdict": "pass"},
                {"item": "deflection", "ratio": r4(v / v_allow), "tolerance": 0.01, "verdict": "pass"},
                {"item": "antislip", "ratio": r4(r_antislip / 8.0), "tolerance": 0.01, "verdict": "pass"}
            ],
            "intermediate": {
                "qk_kN_per_m": r4(qk), "qd_kN_per_m": r4(qd),
                "M_design_kNm": r4(m_design), "sigma_N_per_mm2": r4(sigma),
                "v_mm": r4(v), "v_allow_mm": r4(v_allow),
                "R_kN": r4(r_antislip), "Rc_kN": 8.0
            }
        }
    }


def example_zonggan_001():
    """M-3 纵向水平杆（三跨连续梁+跨中集中力）：抗弯+扣件抗滑。"""
    la, lb = 1.5, 1.05
    board_l, q_live = 0.30, 2.0
    qd = 1.2 * board_l * la + 1.4 * q_live * la
    p_d = qd * lb / 2.0                      # 横杆反力=纵杆集中力
    m_design = 0.175 * p_d * la              # 边跨跨中（三弯矩方程：支座-0.150Pl）
    sigma = m_design * 1e6 / W_MM3
    r_support = 1.15 * p_d                   # 内支座反力（立杆扣件处）
    assert abs(p_d - 2.4885) < 1e-9, p_d
    assert abs(m_design - 0.65323125) < 1e-7, m_design
    assert abs(sigma - 124.1873) < 0.01, sigma
    return {
        "example_id": "EX-shuipinggan-zx-001",
        "title": "纵向水平杆抗弯强度（三跨连续梁+跨中集中力）",
        "module": "M-3",
        "source": SOURCE_130,
        "input_card": {
            "category": "coupler_steel_pipe_scaffold", "rows": "double",
            "member": "long",
            "step_m": 1.8, "long_spacing_m": la, "cross_spacing_m": lb,
            "pipe_spec": "48.3x3.6", "steel_grade": "Q235A",
            "loads": {"board_kN_per_m2": board_l, "live_kN_per_m2": q_live},
            "model_notes": [
                "三跨等跨连续梁（跨度 la），每跨跨中集中力 P=横向水平杆反力（5.2.4）",
                "弯矩系数：支座 -0.150P·la、边跨跨中 0.175P·la、中跨跨中 0.100P·la（三弯矩方程导出）",
                "内支座反力 R=1.15P（扣件抗滑 5.2.5）",
                "挠度本例不设 check（连续梁挠度系数按《建筑结构静力计算手册》，M2 实现时另立参数扫描锁定单调性）"
            ]
        },
        "expect": {
            "checks": [
                {"item": "bending_strength", "ratio": r4(sigma / F130), "tolerance": 0.01, "verdict": "pass"},
                {"item": "antislip", "ratio": r4(r_support / 8.0), "tolerance": 0.01, "verdict": "pass"}
            ],
            "intermediate": {
                "P_design_kN": r4(p_d), "M_design_kNm": r4(m_design),
                "sigma_N_per_mm2": r4(sigma), "R_kN": r4(r_support), "Rc_kN": 8.0
            }
        }
    }


def example_lianqiangjian_001():
    """M-4 连墙件（双排 3h×3la，小风压，全项通过）。"""
    h, la = 1.8, 1.5
    aw = 3 * h * 3 * la                      # 表6.4.2 双排落地 3h×3la=24.3 m²
    wk = 0.10                                # 钉死输入（μz·μs·w0 合成结果）
    n0 = 3.0                                 # 双排（5.2.12）
    nlw = 1.4 * wk * aw
    nl = nlw + n0
    tie_len = 1.35                           # 连墙杆长度 m（钉死输入）
    lam = math.ceil(tie_len * 1000.0 / I_MM)
    phi = PHI[lam]                           # 85 → 0.692
    sigma_strength = nl * 1000.0 / A_MM2
    sigma_stab = nl * 1000.0 / (phi * A_MM2)
    f85 = 0.85 * F130
    assert abs(aw - 24.3) < 1e-9
    assert abs(nl - 6.402) < 1e-9, nl
    assert abs(sigma_stab - 18.2834) < 0.01, sigma_stab
    return {
        "example_id": "EX-lianqiangjian-001",
        "title": "连墙件强度、稳定与扣件抗滑（全项通过）",
        "module": "M-4",
        "source": SOURCE_130,
        "input_card": {
            "category": "coupler_steel_pipe_scaffold", "rows": "double",
            "build_height_m": 12.0,
            "step_m": h, "long_spacing_m": la, "wall_tie": "two_step_three_span",
            "tie_type": "steel_pipe_coupler", "tie_length_m": tie_len,
            "pipe_spec": "48.3x3.6", "steel_grade": "Q235A",
            "wind": {"wk_kN_per_m2": wk},
            "model_notes": [
                "Aw=3h×3la（表6.4.2 双排落地，覆盖面积≤40m² 本例 24.3 满足）",
                "Nl=Nlw+N0（式5.2.12-3，双排 N0=3.0kN）",
                "连墙件 φ48.3×3.6 钢管，两端铰接 l0=1.35m，λ=ceil(l0/i) 查表A.0.6",
                "钢管扣件连墙件需验算扣件抗滑 R≤Rc=8.0kN（5.2.15）"
            ]
        },
        "expect": {
            "checks": [
                {"item": "tie_strength", "ratio": r4(sigma_strength / f85), "tolerance": 0.01, "verdict": "pass"},
                {"item": "tie_stability", "ratio": r4(sigma_stab / f85), "tolerance": 0.01, "verdict": "pass"},
                {"item": "antislip", "ratio": r4(nl / 8.0), "tolerance": 0.01, "verdict": "pass"}
            ],
            "intermediate": {
                "Aw_m2": r4(aw), "Nlw_kN": r4(nlw), "N0_kN": n0, "Nl_kN": r4(nl),
                "lambda": lam, "phi": phi,
                "sigma_strength_N_per_mm2": r4(sigma_strength),
                "sigma_stab_N_per_mm2": r4(sigma_stab), "f85_N_per_mm2": f85
            }
        }
    }


def example_lianqiangjian_002_fail():
    """M-4 不合格路径：大风压下扣件抗滑不满足。"""
    h, la = 1.8, 1.5
    aw = 3 * h * 3 * la
    wk = 0.32
    n0 = 3.0
    nlw = 1.4 * wk * aw
    nl = nlw + n0
    tie_len = 1.35
    lam = math.ceil(tie_len * 1000.0 / I_MM)
    phi = PHI[lam]
    sigma_strength = nl * 1000.0 / A_MM2
    sigma_stab = nl * 1000.0 / (phi * A_MM2)
    f85 = 0.85 * F130
    assert abs(nl - 13.8864) < 1e-9, nl
    assert nl / 8.0 > 1.0
    return {
        "example_id": "EX-lianqiangjian-002",
        "title": "连墙件扣件抗滑不满足（不合格例）",
        "module": "M-4",
        "source": SOURCE_130,
        "input_card": dict(example_lianqiangjian_001()["input_card"],
                           wind={"wk_kN_per_m2": wk}),
        "expect": {
            "checks": [
                {"item": "tie_strength", "ratio": r4(sigma_strength / f85), "tolerance": 0.01, "verdict": "pass"},
                {"item": "tie_stability", "ratio": r4(sigma_stab / f85), "tolerance": 0.01, "verdict": "pass"},
                {"item": "antislip", "ratio": r4(nl / 8.0), "tolerance": 0.01, "verdict": "fail"}
            ],
            "intermediate": {
                "Aw_m2": r4(aw), "Nlw_kN": r4(nlw), "N0_kN": n0, "Nl_kN": r4(nl),
                "lambda": lam, "phi": phi,
                "sigma_strength_N_per_mm2": r4(sigma_strength),
                "sigma_stab_N_per_mm2": r4(sigma_stab), "f85_N_per_mm2": f85
            },
            "verdict_note": "整体判定=不合格（抗滑超限）；建议措施：双扣件/焊接连接或改为刚性连墙件并复算"
        }
    }


def example_diji_001():
    """M-5 立杆地基承载力（回填土地基）。"""
    nk = 1.554 + 1.1325 + 1.575              # Nk=NG1k+NG2k+NQk（标准值）
    pad_a = 0.08                             # 垫板 0.2m×0.4m
    fgk, reduction = 180.0, 0.4              # 勘察报告特征值 × 回填土折减 0.4（5.5.2）
    fg = fgk * reduction
    pk = nk / pad_a
    assert abs(nk - 4.2615) < 1e-9, nk
    assert abs(pk - 53.26875) < 1e-6, pk
    return {
        "example_id": "EX-diji-001",
        "title": "立杆地基承载力（回填土）",
        "module": "M-5",
        "source": SOURCE_130,
        "input_card": {
            "category": "coupler_steel_pipe_scaffold",
            "foundation": {"type": "回填土", "fgk_kPa": fgk, "reduction": reduction,
                           "pad_m": [0.4, 0.2], "nk_kN": nk},
            "loads_note": "Nk 取 EX-lizhigan-nw-001 同参数标准组合（永久+施工，分项系数 1.0）",
            "model_notes": ["pk=Nk/A≤fg（式5.5.1）；fg=fgk×0.4（回填土，5.5.2）"]
        },
        "expect": {
            "checks": [{"item": "foundation_bearing", "ratio": r4(pk / fg), "tolerance": 0.01, "verdict": "pass"}],
            "intermediate": {"Nk_kN": r4(nk), "A_m2": pad_a, "pk_kPa": r4(pk),
                             "fg_kPa": r4(fg)}
        }
    }


def example_muban_nw_001():
    """M-6 模板支架立杆稳定·不组合风（JGJ162）。"""
    g1k, g2k, g3k = 0.75, 24.0 * 0.12, 1.1 * 0.12   # 表4.1.1 木模板含支架（层高<4m）；板厚120mm
    q1k, spacing = 1.0, 1.0                          # 支架立柱活荷载；立杆间距 1.0×1.0m
    h = 1.5                                          # 步距（≤1.8m，5.2.5-3）
    ng = (g1k + g2k + g3k) * spacing * spacing
    n = 0.9 * (1.2 * ng + 1.4 * q1k * spacing * spacing)   # γ0=0.9（4.3.1）
    l0 = h * 1000.0                                  # 计算长度=最大步距（5.2.5-3，无 μ）
    lam = math.ceil(l0 / I_MM)                       # 94.34→95
    phi = PHI[lam]
    sigma = n * 1000.0 / (phi * A_MM2)
    ratio = sigma / F162
    assert abs(ng - 3.762) < 1e-9, ng
    assert abs(n - 5.32296) < 1e-9, n
    assert abs(sigma - 16.8046) < 0.01, sigma
    return {
        "example_id": "EX-mubanzhijia-nw-001",
        "title": "模板支架立杆稳定性（不组合风，JGJ 162-2008）",
        "module": "M-6",
        "source": SOURCE_162,
        "input_card": {
            "category": "formwork_support",
            "slab_thickness_m": 0.12, "story_height_m": 3.9,
            "step_m": h, "pole_spacing_m": [spacing, spacing],
            "pipe_spec": "48.3x3.6", "steel_grade": "Q235",
            "wind": "不组合",
            "loads": {"g1k_kN_per_m2": g1k, "concrete_kN_per_m3": 24.0,
                      "rebar_kN_per_m3_slab": 1.1, "q1k_kN_per_m2": q1k},
            "model_notes": [
                "组合按表4.3.2 第1项：承载能力 G1k+G2k+G3k+Q1k，γ0=0.9（4.3.1）",
                "扣件钢管立柱按单杆轴心受压（5.2.5-3），l0=最大步距 1.5m（≤1.8m 满足）",
                "λ=ceil(l0/i) 查 φ（162 附录D=GB50017 系表，数值按 JGJ130 表A.0.6）",
                "f=215 N/mm²（162 表A.1.1-1 Q235 t≤16；不得用 JGJ130 的 205）"
            ]
        },
        "expect": {
            "checks": [{"item": "column_stability", "ratio": r4(ratio), "tolerance": 0.01, "verdict": "pass"}],
            "intermediate": {"NG_kN": r4(ng), "N_design_kN": r4(n),
                             "lambda": lam, "phi": phi,
                             "sigma_N_per_mm2": r4(sigma), "f": F162}
        }
    }


def example_muban_w_001():
    """M-6 模板支架立杆稳定·组合风（室外露天）。"""
    g1k, g2k, g3k = 0.75, 24.0 * 0.12, 1.1 * 0.12
    q1k = 1.0
    la, lb, h = 1.0, 1.0, 1.5
    wk = 0.30                                 # 钉死输入（162 4.1.3 按 GB50009 n=10、βz=1 的合成结果）
    ng = (g1k + g2k + g3k) * la * lb
    mwk = wk * la * (h ** 2) / 10.0
    mw = 0.9 ** 2 * 1.4 * mwk                 # 式5.2.5-15
    nqik = q1k * la * lb + mw / lb            # 另加 Mw/lb（5.2.5-3）
    nw = 0.9 * (1.2 * ng + 0.9 * 1.4 * nqik)  # 式5.2.5-14（整体再包 γ0=0.9? 规范式即含 0.9 外包）
    l0 = h * 1000.0
    lam = math.ceil(l0 / I_MM)
    phi = PHI[lam]
    sigma = nw * 1000.0 / (phi * A_MM2) + (mw * 1e6) / W_MM3
    ratio = sigma / F162
    assert abs(mw - 0.076545) < 1e-9, mw
    assert abs(nw - 5.28376203) < 1e-6, nw
    assert abs(sigma - 31.2264) < 0.02, sigma
    return {
        "example_id": "EX-mubanzhijia-w-001",
        "title": "模板支架立杆稳定性（组合风，室外露天，JGJ 162-2008）",
        "module": "M-6",
        "source": SOURCE_162,
        "input_card": {
            "category": "formwork_support",
            "slab_thickness_m": 0.12, "story_height_m": 3.9,
            "step_m": h, "pole_spacing_m": [la, lb],
            "pipe_spec": "48.3x3.6", "steel_grade": "Q235",
            "wind": {"wk_kN_per_m2": wk},
            "loads": {"g1k_kN_per_m2": g1k, "concrete_kN_per_m3": 24.0,
                      "rebar_kN_per_m3_slab": 1.1, "q1k_kN_per_m2": q1k},
            "model_notes": [
                "室外露天支模组合风（5.2.5-3 第2项）：式5.2.5-13/-14/-15",
                "NQik 另加 Mw/lb；λ=ceil(l0/i)；f=215（表A.1.1-1）"
            ]
        },
        "expect": {
            "checks": [{"item": "column_stability", "ratio": r4(ratio), "tolerance": 0.01, "verdict": "pass"}],
            "intermediate": {"Mwk_kNm": r4(mwk), "Mw_kNm": r4(mw),
                             "NQik_kN": r4(nqik), "Nw_kN": r4(nw),
                             "lambda": lam, "phi": phi,
                             "sigma_N_per_mm2": r4(sigma), "f": F162}
        }
    }


def example_diji_162_001():
    """M-6 立柱地基（JGJ162 5.2.6，原土地基）。"""
    n = 5.32296                               # EX-mubanzhijia-nw-001 的设计值
    pad_a = 0.10                              # 垫木 0.5m×0.2m
    mf, fak = 0.9, 100.0                      # 表5.2.6 粉土黏土原土 mf=0.9
    p = n / pad_a
    assert abs(p - 53.2296) < 1e-6, p
    return {
        "example_id": "EX-diji-162-001",
        "title": "立柱底地基承载力（JGJ 162-2008，原土）",
        "module": "M-6",
        "source": SOURCE_162,
        "input_card": {
            "category": "formwork_support",
            "foundation": {"soil": "粉土、黏土", "on_backfill": False, "mf": mf,
                           "fak_kPa": fak, "pad_m": [0.5, 0.2], "n_design_kN": 5.32296},
            "loads_note": "N 取 EX-mubanzhijia-nw-001 设计值（含 γ0=0.9）",
            "model_notes": ["p=N/A≤mf·fak（5.2.6）"]
        },
        "expect": {
            "checks": [{"item": "foundation_bearing", "ratio": r4(p / (mf * fak)), "tolerance": 0.01, "verdict": "pass"}],
            "intermediate": {"N_kN": r4(n), "A_m2": pad_a, "p_kPa": r4(p),
                             "mf": mf, "fak_kPa": fak}
        }
    }


def main():
    write = "--check" not in sys.argv
    builders = [
        example_lizhigan_nw_001, example_lizhigan_nw_002, example_lizhigan_nw_003_fail,
        example_lizhigan_w_001, example_lizhigan_w_002,
        example_henggan_001, example_zonggan_001,
        example_lianqiangjian_001, example_lianqiangjian_002_fail,
        example_diji_001,
        example_muban_nw_001, example_muban_w_001, example_diji_162_001,
    ]
    out_dir = os.path.join("data", "examples")
    if write:
        os.makedirs(out_dir, exist_ok=True)
    for build in builders:
        ex = build()
        checks = ex["expect"]["checks"]
        assert checks, ex["example_id"]
        for c in checks:
            expect_verdict = "pass" if c["ratio"] <= 1.0 else "fail"
            assert c["verdict"] == expect_verdict, (ex["example_id"], c)
        line = "%-26s %-9s ratio=%-8.4f %s" % (
            ex["example_id"],
            ",".join(c["verdict"] for c in checks),
            checks[0]["ratio"], ex["title"])
        print(line)
        if write:
            path = os.path.join(out_dir, ex["example_id"] + ".json")
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                json.dump(ex, f, ensure_ascii=False, indent=2, sort_keys=False)
                f.write("\n")
    print("total:", len(builders))
    return 0


if __name__ == "__main__":
    sys.exit(main())
