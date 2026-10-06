# -*- coding: utf-8 -*-
"""M2 条款库加载器：装配 formulas.json + thresholds.json，执行"待核对硬拦截"。

条文纪律（plan/04 §3、plan/06 #4）：任一依赖条目 status=待核对 → 该模块整体
返回"不可验算（依据未核对）"，而非带病计算。拦截在两层生效：
1. Knowledge.unverified(module_id)：模块依赖面体检（CLI/引擎运行前调用）；
2. Knowledge.threshold()：数值取用时逐条校验（即使模块级漏拦也取不到值）。
"""

import json
import os

# 模块依赖面（与 tests/test_clause_library.py::test_engine_module_dependencies_all_verified 同一口径；
# 新增依赖须两处同步，否则测试打挂）
MODULE_DEPS = {
    "M-1": {
        "formulas": ["F-J130-stab-nw", "F-J130-N-nw", "F-J130-l0", "F-J130-wk", "F-J130-beam-strength"],
        "thresholds": [
            "T-JGJ130-section-props", "T-JGJ130-steel-design", "T-JGJ130-phi-table",
            "T-JGJ130-mu-coef", "T-JGJ130-gk-table", "T-JGJ130-partial-factors",
            "T-JGJ130-dead-loads", "T-JGJ130-live-loads",
        ],
    },
    "M-2": {
        "formulas": ["F-J130-stab-w", "F-J130-N-w", "F-J130-Mw", "F-J130-wk"],
        "thresholds": [
            "T-JGJ130-section-props", "T-JGJ130-steel-design", "T-JGJ130-phi-table",
            "T-JGJ130-mu-coef", "T-JGJ130-gk-table", "T-JGJ130-partial-factors",
            "T-JGJ130-dead-loads", "T-JGJ130-live-loads", "T-JGJ130-shape-coef",
        ],
    },
    "M-3": {
        "formulas": ["F-J130-beam-strength", "F-J130-beam-M", "F-J130-beam-deflection", "F-J130-antislip"],
        "thresholds": [
            "T-JGJ130-section-props", "T-JGJ130-steel-design", "T-JGJ130-deflection-limits",
            "T-JGJ130-coupler-capacity", "T-JGJ130-partial-factors",
        ],
    },
    "M-4": {
        "formulas": ["F-J130-tie-strength", "F-J130-tie-stab", "F-J130-tie-N", "F-J130-tie-Nlw"],
        "thresholds": [
            "T-JGJ130-section-props", "T-JGJ130-steel-design", "T-JGJ130-phi-table",
            "T-JGJ130-tie-N0", "T-JGJ130-walltie-spacing", "T-JGJ130-coupler-capacity",
        ],
    },
    "M-5": {
        "formulas": ["F-J130-foundation"],
        "thresholds": ["T-JGJ130-fg-reduction"],
    },
    "M-6": {
        "formulas": ["F-J162-column", "F-J162-column-w", "F-J162-Nw", "F-J162-Mw", "F-J162-foundation"],
        "thresholds": [
            "T-JGJ130-section-props", "T-JGJ162-steel-design", "T-JGJ130-phi-table",
            "T-JGJ162-partial-factors", "T-JGJ162-column-step", "T-JGJ162-fg-reduction",
            "T-JGJ162-dead-loads", "T-JGJ162-live-loads",
        ],
    },
}

_CLAUSE_FILES = ("jgj130_clauses.json", "jgj162_clauses.json",
                 "decree37_clauses.json", "notice31_clauses.json")


class KnowledgeError(Exception):
    """条款库不可用（缺文件/结构坏）。按输入不可用处置（CLI exit 2）。"""


def find_data_dir(explicit=None):
    """数据目录查找：显式参数 > SFC_DATA 环境变量 > CWD 上溯 > 包相对上溯（开发树）。

    显式参数（--data-dir / 环境变量）不合法时立即返回 None（不静默回退到自动发现，
    防止"指错目录却跑出别处数据"）；仅自动发现路径走逐级回退。
    打包内嵌分支（sys._MEIPASS 等）按 plan/03 D8 于 M5 冻结实现，此处留扩展位。
    """
    if explicit:
        if os.path.isdir(os.path.join(explicit, "knowledge", "clauses")):
            return explicit
        return None
    env = os.environ.get("SFC_DATA")
    if env:
        if os.path.isdir(os.path.join(env, "knowledge", "clauses")):
            return env
        return None
    candidates = []
    base = os.getcwd()
    for _ in range(5):
        candidates.append(os.path.join(base, "data"))
        parent = os.path.dirname(base)
        if parent == base:
            break
        base = parent
    # 包相对上溯：src/scaffold_formwork_checker/engine/loader.py → 仓库根/data（开发树）
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(here, "..", "..", "..", "data"))
    for cand in candidates:
        if cand and os.path.isdir(os.path.join(cand, "knowledge", "clauses")):
            return cand
    return None


class Knowledge(object):
    """条款库运行时视图：公式表/阈值表 + 模块依赖面拦截。"""

    def __init__(self, data_dir):
        self.data_dir = data_dir
        clauses_dir = os.path.join(data_dir, "knowledge", "clauses")
        self.formulas = self._load(clauses_dir, "formulas.json")["formulas"]
        self.thresholds = self._load(clauses_dir, "thresholds.json")["thresholds"]
        self.clauses = {}
        for fname in _CLAUSE_FILES:
            doc = self._load(clauses_dir, fname)
            for c in doc["clauses"]:
                self.clauses[c["clause_id"]] = c
        self._formula_by_id = {f["formula_id"]: f for f in self.formulas}
        self._threshold_by_id = {t["threshold_id"]: t for t in self.thresholds}

    @staticmethod
    def _load(clauses_dir, name):
        path = os.path.join(clauses_dir, name)
        if not os.path.isfile(path):
            raise KnowledgeError("条款库文件缺失：%s" % path)
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except ValueError as exc:
            raise KnowledgeError("条款库 JSON 解析失败 %s：%s" % (path, exc))

    # ---- 硬拦截 ----

    def unverified(self, module_id):
        """返回模块依赖面中 status!=已核对 的条目 id 列表（空=可验算）。"""
        if module_id not in MODULE_DEPS:
            raise KnowledgeError("未知模块 %r" % (module_id,))
        bad = []
        deps = MODULE_DEPS[module_id]
        for fid in deps["formulas"]:
            f = self._formula_by_id.get(fid)
            if f is None:
                bad.append(fid)
            elif f.get("status") != "已核对":
                bad.append(fid)
        for tid in deps["thresholds"]:
            t = self._threshold_by_id.get(tid)
            if t is None:
                bad.append(tid)
            elif t.get("status") != "已核对":
                bad.append(tid)
        return bad

    def formula(self, formula_id):
        """取公式条目；待核对/缺失即抛 KnowledgeError（第二层拦截）。"""
        f = self._formula_by_id.get(formula_id)
        if f is None:
            raise KnowledgeError("公式条目不存在：%s" % formula_id)
        if f.get("status") != "已核对":
            raise KnowledgeError("公式 %s status=%s，不得进入计算路径"
                                 % (formula_id, f.get("status")))
        return f

    def threshold(self, threshold_id):
        """取阈值条目；待核对/缺失即抛 KnowledgeError（第二层拦截）。"""
        t = self._threshold_by_id.get(threshold_id)
        if t is None:
            raise KnowledgeError("阈值条目不存在：%s" % threshold_id)
        if t.get("status") != "已核对":
            raise KnowledgeError("阈值 %s status=%s，不得进入计算路径"
                                 % (threshold_id, t.get("status")))
        return t

    def threshold_value(self, threshold_id):
        return self.threshold(threshold_id)["value"]

    def clause(self, clause_id):
        return self.clauses.get(clause_id)


def load_knowledge(data_dir=None):
    """定位并加载条款库；找不到数据目录抛 KnowledgeError。"""
    resolved = find_data_dir(data_dir)
    if resolved is None:
        raise KnowledgeError(
            "未找到数据目录（含 knowledge/clauses）：可用 --data-dir 指定或设 SFC_DATA"
        )
    return Knowledge(resolved)
