# -*- coding: utf-8 -*-
"""条款库/公式表/阈值表/危大清单结构纪律守门（M1 DoD ①：100% 挂出处或待核对）。"""

import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAUSES_DIR = os.path.join(REPO_ROOT, "data", "knowledge", "clauses")


def _load(name):
    with open(os.path.join(CLAUSES_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def test_all_clauses_have_status_and_source():
    for fname in ("jgj130_clauses.json", "jgj162_clauses.json",
                  "decree37_clauses.json", "notice31_clauses.json"):
        doc = _load(fname)
        assert doc["clauses"], fname
        for c in doc["clauses"]:
            assert c["status"] in ("已核对", "待核对"), (fname, c["clause_id"])
            assert c["source"].get("file") and c["source"].get("channel"), (fname, c["clause_id"])
            assert c["excerpt"], (fname, c["clause_id"])
            assert c["gist"], (fname, c["clause_id"])


def test_formulas_and_thresholds_fully_graded():
    formulas = _load("formulas.json")["formulas"]
    thresholds = _load("thresholds.json")["thresholds"]
    for x in formulas + thresholds:
        assert x["status"] in ("已核对", "待核对"), x.get("formula_id") or x.get("threshold_id")
        assert x.get("clause_ref") or x.get("clause_refs"), x


def test_engine_module_dependencies_all_verified():
    """5+1 验算模块所需公式/阈值全部 status=已核对（待核对硬拦截的前置）。"""
    formulas = {x["formula_id"]: x for x in _load("formulas.json")["formulas"]}
    thresholds = {x["threshold_id"]: x for x in _load("thresholds.json")["thresholds"]}
    module_formulas = {
        "M-1": ["F-J130-stab-nw", "F-J130-N-nw", "F-J130-l0", "F-J130-wk", "F-J130-beam-strength"],
        "M-2": ["F-J130-stab-w", "F-J130-N-w", "F-J130-Mw", "F-J130-wk"],
        "M-3": ["F-J130-beam-strength", "F-J130-beam-M", "F-J130-beam-deflection", "F-J130-antislip"],
        "M-4": ["F-J130-tie-strength", "F-J130-tie-stab", "F-J130-tie-N", "F-J130-tie-Nlw"],
        "M-5": ["F-J130-foundation"],
        "M-6": ["F-J162-column", "F-J162-column-w", "F-J162-Nw", "F-J162-Mw", "F-J162-foundation"],
    }
    for module, fids in module_formulas.items():
        for fid in fids:
            assert fid in formulas, (module, fid)
            assert formulas[fid]["status"] == "已核对", (module, fid)
            for ref in formulas[fid].get("clause_refs", []):
                assert ref, (module, fid)
    # 模块阈值依赖
    for tid in ("T-JGJ130-section-props", "T-JGJ130-steel-design", "T-JGJ162-steel-design",
                "T-JGJ130-phi-table", "T-JGJ130-mu-coef", "T-JGJ130-gk-table",
                "T-JGJ162-partial-factors", "T-JGJ162-column-step"):
        assert thresholds[tid]["status"] == "已核对", tid


def test_pending_formula_not_in_engine_path():
    """status=待核对 的公式不得被任何模块公式引用（条文纪律，M2 加载器同口径）。"""
    formulas = {x["formula_id"]: x for x in _load("formulas.json")["formulas"]}
    pending = {fid for fid, x in formulas.items() if x["status"] == "待核对"}
    assert "F-J162-sidepressure" in pending
    for x in formulas.values():
        for pid in x.get("params", {}) or {}:
            src = (x["params"][pid] or {}).get("source", "")
            assert src not in pending, (x["formula_id"], pid, src)


CLAUSE_FILES = ("jgj130_clauses.json", "jgj162_clauses.json",
                "decree37_clauses.json", "notice31_clauses.json")


def test_verified_clause_never_cites_pending_formula():
    """已核对条款的 formula_refs 必须全部指向已核对公式（SI-020）。

    缺口（2026-10-23 实测）：`JGJ162-4.1.1` 自身 `status=已核对`，但
    `formula_refs` 指向 `status=待核对` 的 `F-J162-sidepressure`。全仓原有测试
    只校验「待核对公式不得被**模块**引用」（上一函数），没人校验「**条款**引用的公式
    本身是否核对过」——于是一条已核对条款在机读层面"引用"了未经核对的数值来源。

    处置口径：不伪造核对结论（不把侧压力公式转 已核对）。未核对的引用移入
    `pending_formula_refs`，与 `formula_refs`（已验证面）分离；计算路径读前者之外
    的字段，故不改变任何数值结论。
    """
    formulas = {x["formula_id"]: x["status"] for x in _load("formulas.json")["formulas"]}
    offenders = []
    for fname in CLAUSE_FILES:
        for c in _load(fname)["clauses"]:
            for fid in c.get("formula_refs") or []:
                assert fid in formulas, ("条款引用了不存在的公式", fname, c["clause_id"], fid)
                if formulas[fid] != "已核对":
                    offenders.append((fname, c["clause_id"], fid, formulas[fid]))
    assert not offenders, (
        "已核对条款不得在 formula_refs 里引用未核对公式"
        "（应移入 pending_formula_refs）：%r" % (offenders,)
    )


def test_pending_formula_refs_still_traceable():
    """被移出 formula_refs 的待核对引用必须留在 pending_formula_refs 里（不许直接删）。

    这是上一条的反向守门：允许「未核对的引用」存在，但必须**显式标记**为待核对，
    否则修 SI-020 的最省事写法（把 refs 清空）会把可追溯性一起删掉。
    """
    formulas = {x["formula_id"]: x["status"] for x in _load("formulas.json")["formulas"]}
    traced = {}
    for fname in CLAUSE_FILES:
        for c in _load(fname)["clauses"]:
            for fid in c.get("pending_formula_refs") or []:
                assert fid in formulas, ("pending 引用了不存在的公式", fname, c["clause_id"], fid)
                assert formulas[fid] != "已核对", (
                    "公式 %s 已转 已核对，应移回 formula_refs 而不是留在 pending_formula_refs"
                    % fid)
                traced.setdefault(fid, []).append(c["clause_id"])
    # 当前唯一待核对公式必须仍被至少一条条款登记
    pending_all = {fid for fid, st in formulas.items() if st != "已核对"}
    for fid in pending_all:
        assert fid in traced, "待核对公式 %s 没有任何条款登记（追溯断链）" % fid



def test_panorama_items_have_excerpts_and_levels():
    pano = _load("panorama.json")
    assert len(pano["items"]) >= 8
    for item in pano["items"]:
        assert item["project_type"] and item["judge_params"] is not None
        assert set(item["levels"].keys()) >= {"none", "weida", "chaoguimo"}
        for b in item["basis"]:
            assert b["excerpt"], item["item_id"]
            assert b["status"] == "已核对", item["item_id"]
            assert b["channel"], item["item_id"]
        # 24m/50m 边界语义抽查
    luodi = [i for i in pano["items"] if i["item_id"] == "pan-luodi-gangguan-24"][0]
    assert luodi["levels"]["weida"]["cond"] == "24 <= build_height < 50"
    assert luodi["levels"]["chaoguimo"]["cond"] == "build_height >= 50"
    assert "24m" in luodi["basis"][0]["excerpt"]
    assert "50m" in luodi["basis"][1]["excerpt"]
