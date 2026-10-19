# -*- coding: utf-8 -*-
"""条款库「复核机制」守门（v2.0.0 新增，plan/06 #35 迭代批次 3.6）。

背景（update/00-诊断报告 D4/D8）：条款库此前只有「核对过」（status=已核对），
没有任何「何时该复核」的机制；`panorama.json` 的核对状态只存在于 `basis[]`
子对象，条目级 `status` 为 None，机器扫不到。

本测试把"复核机制"钉死成可机检断言：
1. 每个条款库文件都有 `meta.review`，且 reviewed_on / next_review_due /
   cycle_months / standards 全部非空、日期可解析、下次复核日晚于本次复核日；
2. `meta.review.standards[*].authority_url` 非空（复核必须有出处，不接受"据我所知"）；
3. `panorama.json` 每个条目级 `status` 非空，且与 `basis[*].status` 集合一致
   （集合内不一致即条目级结论不可靠）；
4. 被 3.5 判定为"本版本不依赖"的待核对公式，必须显式声明 `not_used_by`
   且该声明与真实模块依赖面吻合（防"嘴上说不依赖、实际被引用"）。
"""

import json
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAUSES_DIR = os.path.join(REPO_ROOT, "data", "knowledge", "clauses")

CLAUSE_FILES = (
    "jgj130_clauses.json",
    "jgj162_clauses.json",
    "decree37_clauses.json",
    "notice31_clauses.json",
    "formulas.json",
    "thresholds.json",
    "panorama.json",
)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# 模块依赖面（与 engine/loader.py MODULE_DEPS 同口径；新增依赖两处同步）
MODULE_FORMULA_DEPS = {
    "M-1": ["F-J130-stab-nw", "F-J130-N-nw", "F-J130-l0", "F-J130-wk", "F-J130-beam-strength"],
    "M-2": ["F-J130-stab-w", "F-J130-N-w", "F-J130-Mw", "F-J130-wk"],
    "M-3": ["F-J130-beam-strength", "F-J130-beam-M", "F-J130-beam-deflection", "F-J130-antislip"],
    "M-4": ["F-J130-tie-strength", "F-J130-tie-stab", "F-J130-tie-N", "F-J130-tie-Nlw"],
    "M-5": ["F-J130-foundation"],
    "M-6": ["F-J162-column", "F-J162-column-w", "F-J162-Nw", "F-J162-Mw", "F-J162-foundation"],
}


def _load(name):
    with open(os.path.join(CLAUSES_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def _review(doc, name):
    meta = doc["meta"]
    assert "review" in meta, "%s 缺 meta.review（复核机制未落地）" % name
    return meta["review"]


def test_every_clause_file_has_review_metadata():
    """① 每个文件都有非空复核元数据，且日期自洽。"""
    for name in CLAUSE_FILES:
        review = _review(_load(name), name)
        for key in ("reviewed_on", "next_review_due"):
            assert review.get(key), "%s meta.review.%s 为空" % (name, key)
            assert _DATE_RE.match(review[key]), "%s meta.review.%s 非 ISO 日期：%r" % (
                name, key, review[key])
        assert review["next_review_due"] > review["reviewed_on"], (
            "%s 下次复核日不晚于本次复核日" % name)
        assert isinstance(review.get("cycle_months"), int) and review["cycle_months"] > 0, (
            "%s meta.review.cycle_months 非法" % name)
        assert review.get("reviewer"), "%s meta.review.reviewer 为空" % name


def test_review_standards_carry_authority_url():
    """② 复核结论必须有出处（URL 非空），不接受"据我所知仍然有效"。"""
    for name in CLAUSE_FILES:
        review = _review(_load(name), name)
        stds = review.get("standards")
        assert isinstance(stds, list) and stds, "%s meta.review.standards 为空" % name
        for s in stds:
            assert s.get("standard"), (name, s)
            assert s.get("authority_url", "").strip(), "%s %s 缺 authority_url" % (
                name, s.get("standard"))
            assert s.get("conclusion", "").strip(), "%s %s 缺 conclusion" % (
                name, s.get("standard"))
            assert s.get("currency", "").strip(), "%s %s 缺 currency" % (
                name, s.get("standard"))


def test_panorama_item_status_consistent_with_basis():
    """③ panorama 条目级 status 非空且与 basis 级集合一致（D8 闭环）。"""
    pano = _load("panorama.json")
    for item in pano["items"]:
        assert item.get("status"), "panorama 条目 %s 条目级 status 为空" % item["item_id"]
        basis_states = {b["status"] for b in item["basis"]}
        assert basis_states == {item["status"]}, (
            "panorama 条目 %s：条目级 status=%r 与 basis 级 %r 不一致"
            % (item["item_id"], item["status"], sorted(basis_states)))


def test_pending_formula_declares_not_used_explicitly():
    """④ 待核对公式必须显式声明「本版本不依赖」，且与真实依赖面一致。"""
    formulas = {f["formula_id"]: f for f in _load("formulas.json")["formulas"]}
    all_modules = set(MODULE_FORMULA_DEPS)
    pending = {fid for fid, f in formulas.items() if f["status"] == "待核对"}
    assert pending, "本仓库应至少保留 1 项待核对公式（F-J162-sidepressure）作为机制样本"
    for fid in pending:
        f = formulas[fid]
        declared = f.get("not_used_by")
        assert isinstance(declared, list) and declared, (
            "待核对公式 %s 未声明 not_used_by（必须写清本版本是否依赖）" % fid)
        assert f.get("pending_reason", "").strip(), (
            "待核对公式 %s 未写清 pending_reason（已完成项 vs 未完成项）" % fid)
        actually_used = {m for m, fids in MODULE_FORMULA_DEPS.items() if fid in fids}
        assert not (set(declared) & actually_used), (
            "待核对公式 %s 声明不依赖 %r，但被模块 %r 引用（声明与事实不符）"
            % (fid, sorted(set(declared) & actually_used), sorted(actually_used)))
        assert set(declared) == all_modules - actually_used, (
            "待核对公式 %s 的 not_used_by=%r 与真实未引用模块集 %r 不符（漏写或过报）"
            % (fid, sorted(declared), sorted(all_modules - actually_used)))

def test_all_source_fetched_dates_present():
    """⑤ 每个带 source 的条目都必须登记取回日期（fetched 非空且为 ISO 日期）。

    D4 诊断称"fetched 全为 None"；实测 80 处全部已填（见 update/02-执行记录），
    本测试把该事实钉死，防将来回退成 None。
    """
    def walk(o, path, out):
        if isinstance(o, dict):
            if "fetched" in o:
                out.append((path, o["fetched"]))
            for k, v in o.items():
                walk(v, path + "/" + k, out)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, path + "[%d]" % i, out)

    total = 0
    for name in ("jgj130_clauses.json", "jgj162_clauses.json",
                 "decree37_clauses.json", "notice31_clauses.json", "formulas.json"):
        found = []
        walk(_load(name), name, found)
        assert found, "%s 未发现任何 fetched 字段" % name
        for path, value in found:
            assert value, "%s 的 %s 的 fetched 为空" % (name, path)
            assert _DATE_RE.match(value), "%s 的 %s 的 fetched 非 ISO 日期：%r" % (
                name, path, value)
        total += len(found)
    assert total >= 80, "fetched 覆盖数异常偏低：%d（基线 80）" % total
