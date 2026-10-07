# -*- coding: utf-8 -*-
"""bench grading 套件：危大分级判定边界值用例表（M3 DoD ② 口径的正式化）。

与 tests/test_grading.py 同口径：判定序 chaoguimo→weida→none（决策 #25），
边界值 ±ε（"及以上"→>=、"超过"→>），三值逻辑 None=参数缺失 → pending。
指标：通过率（目标 100%）。全套零 API、离线、确定性。
"""

from ..engine.loader import KnowledgeError, find_data_dir
from ..grading import judge, load_panorama


def _muban(height=0.1, span=0.1, total=0.1, linear=0.1, independent=False):
    return {"support_height": height, "support_span": span,
            "total_load_design": total, "linear_load_design": linear,
            "independent_member": independent}


# 用例表：(case_id, item_id, params, expect_status, expect_level)
# expect_level 仅在 expect_status="definite" 时参与对账；pending 用例核对
# unknown_params 非空（note 文本不锁，防措辞调整打挂基准）。
GRADING_CASES = (
    # ---- 落地扣件钢管脚手架（24m/50m 双档边界）----
    ("luodi-h23.9", "pan-luodi-gangguan-24", {"build_height": 23.9}, "definite", "none"),
    ("luodi-h24.0", "pan-luodi-gangguan-24", {"build_height": 24.0}, "definite", "weida"),
    ("luodi-h24.1", "pan-luodi-gangguan-24", {"build_height": 24.1}, "definite", "weida"),
    ("luodi-h49.9", "pan-luodi-gangguan-24", {"build_height": 49.9}, "definite", "weida"),
    ("luodi-h50.0", "pan-luodi-gangguan-24", {"build_height": 50.0}, "definite", "chaoguimo"),
    ("luodi-h50.1", "pan-luodi-gangguan-24", {"build_height": 50.1}, "definite", "chaoguimo"),
    ("luodi-h0", "pan-luodi-gangguan-24", {"build_height": 0.0}, "definite", "none"),
    ("luodi-h12", "pan-luodi-gangguan-24", {"build_height": 12.0}, "definite", "none"),
    ("luodi-h30", "pan-luodi-gangguan-24", {"build_height": 30.0}, "definite", "weida"),
    ("luodi-h56", "pan-luodi-gangguan-24", {"build_height": 56.0}, "definite", "chaoguimo"),
    # ---- 悬挑式（20m 档）----
    ("xuantiao-19.9", "pan-xuantiao-jiaoshoujia", {"segment_height": 19.9}, "definite", "weida"),
    ("xuantiao-20.0", "pan-xuantiao-jiaoshoujia", {"segment_height": 20.0}, "definite", "chaoguimo"),
    ("xuantiao-20.1", "pan-xuantiao-jiaoshoujia", {"segment_height": 20.1}, "definite", "chaoguimo"),
    # ---- 附着式升降（150m 档）----
    ("fuzhuo-149.9", "pan-fuzhuo-shengjiang", {"lift_height": 149.9}, "definite", "weida"),
    ("fuzhuo-150.0", "pan-fuzhuo-shengjiang", {"lift_height": 150.0}, "definite", "chaoguimo"),
    ("fuzhuo-150.1", "pan-fuzhuo-shengjiang", {"lift_height": 150.1}, "definite", "chaoguimo"),
    # ---- 承重支撑（7kN 档）----
    ("chengzhong-6.9", "pan-chengzhong-zhicheng", {"single_point_load": 6.9}, "definite", "weida"),
    ("chengzhong-7.0", "pan-chengzhong-zhicheng", {"single_point_load": 7.0}, "definite", "chaoguimo"),
    ("chengzhong-7.1", "pan-chengzhong-zhicheng", {"single_point_load": 7.1}, "definite", "chaoguimo"),
    # ---- 混凝土模板支撑（危大 5 条件 OR；超规模 4 条件 OR；判定序优先）----
    ("muban-all-small", "pan-muban-zhicheng", _muban(), "definite", "none"),
    ("muban-h4.9", "pan-muban-zhicheng", _muban(height=4.9), "definite", "none"),
    ("muban-h5.0", "pan-muban-zhicheng", _muban(height=5.0), "definite", "weida"),
    ("muban-span9.9", "pan-muban-zhicheng", _muban(span=9.9), "definite", "none"),
    ("muban-span10.0", "pan-muban-zhicheng", _muban(span=10.0), "definite", "weida"),
    ("muban-span18.0", "pan-muban-zhicheng", _muban(span=18.0), "definite", "chaoguimo"),
    ("muban-total9.9", "pan-muban-zhicheng", _muban(total=9.9), "definite", "none"),
    ("muban-total10.0", "pan-muban-zhicheng", _muban(total=10.0), "definite", "weida"),
    ("muban-total15.0", "pan-muban-zhicheng", _muban(total=15.0), "definite", "chaoguimo"),
    ("muban-linear14.9", "pan-muban-zhicheng", _muban(linear=14.9), "definite", "none"),
    ("muban-linear15.0", "pan-muban-zhicheng", _muban(linear=15.0), "definite", "weida"),
    ("muban-linear20.0", "pan-muban-zhicheng", _muban(linear=20.0), "definite", "chaoguimo"),
    ("muban-independent", "pan-muban-zhicheng", _muban(independent=True), "definite", "weida"),
    ("muban-h8.0", "pan-muban-zhicheng", _muban(height=8.0), "definite", "chaoguimo"),
    # ---- 三值 pending（参数缺失 → None，待人工确认，不猜值）----
    ("luodi-pending-missing", "pan-luodi-gangguan-24", {}, "pending", None),
    ("muban-pending-partial", "pan-muban-zhicheng", {"support_height": 3.0}, "pending", None),
)


def run_grading_suite(data_dir=None):
    """grading 套件：用例表逐条判定并汇总通过率。"""
    base = find_data_dir(data_dir)
    if base is None:
        raise KnowledgeError(
            "未找到数据目录（含 knowledge/clauses）：可用 --data-dir 指定或设 SFC_DATA")
    panorama = load_panorama(base)
    per_case = []
    for case_id, item_id, params, expect_status, expect_level in GRADING_CASES:
        result = judge(item_id, params, panorama=panorama)
        failures = []
        if result.get("status") != expect_status:
            failures.append("status %r != 期望 %r" % (result.get("status"), expect_status))
        if expect_status == "definite" and result.get("level") != expect_level:
            failures.append("level %r != 期望 %r" % (result.get("level"), expect_level))
        if expect_status == "pending" and not result.get("unknown_params"):
            failures.append("pending 用例应登记缺失参数（unknown_params 为空）")
        per_case.append({
            "case_id": case_id,
            "item_id": item_id,
            "ok": not failures,
            "failures": failures,
        })
    passed = sum(1 for x in per_case if x["ok"])
    n = len(per_case)
    return {
        "cases": n,
        "passed": passed,
        "pass_rate": (passed / n) if n else 0.0,
        "fail_cases": [x["case_id"] for x in per_case if not x["ok"]],
        "per_case": per_case,
    }


__all__ = ["GRADING_CASES", "run_grading_suite"]
