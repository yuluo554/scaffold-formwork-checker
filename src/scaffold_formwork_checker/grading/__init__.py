# -*- coding: utf-8 -*-
"""M3 危大分级判定器（plan/04 §6）。

判定流程：工程类型识别 → 参数提取（卡取值/显式传入/--param 覆盖）→
逐级条件比较 → 结论+义务+依据摘录。

- 阈值清单 = data/knowledge/clauses/panorama.json（建办质〔2018〕31号
  附件1/附件2 中脚手架/模板相关 9 条目，逐条挂原文摘录与核对状态）；
- 条件表达式为清单自带字符串（如 "24 <= build_height < 50"、
  "a >= 5 || b >= 10 || !(flag)"），由自研三值求值器执行：
  True / False / None（None=参数缺失，待人工确认），不使用 eval；
- 分级依据 basis 全部 status=已核对 才出确定结论，否则 pending（条文纪律）；
- 边界语义按 meta.boundary_semantics："及以上"→>=，"超过"→>（原文措辞映射）。
"""

import json
import os
import re

from ..engine.loader import KnowledgeError, find_data_dir

LEVEL_NONE = "none"
LEVEL_WEIDA = "weida"
LEVEL_CHAOGUIMO = "chaoguimo"

# 判定结论 rule_id（真值锁定：落地架超规模档=G-pan-luodi-50；其余默认 G-<item_id>）
_RULE_ID_SPECIAL = {
    ("pan-luodi-gangguan-24", LEVEL_WEIDA): "G-pan-luodi-24",
    ("pan-luodi-gangguan-24", LEVEL_CHAOGUIMO): "G-pan-luodi-50",
}

# 类型识别关键词（顺序即优先级：具体类型在前，落地兜底在后）
_TYPE_KEYWORDS = (
    ("pan-gongjushi-muban", ("工具式模板", "滑模", "爬模", "飞模", "隧道模")),
    ("pan-chengzhong-zhicheng", ("承重支撑", "满堂支撑体系")),
    ("pan-muban-zhicheng", ("模板支撑", "模板支架")),
    ("pan-fuzhuo-shengjiang", ("附着式升降",)),
    ("pan-xuantiao-jiaoshoujia", ("悬挑",)),
    ("pan-gaochudiaolan", ("吊篮",)),
    ("pan-xieliao-pingtai", ("卸料平台", "操作平台")),
    ("pan-yixing-jiaoshoujia", ("异型脚手架", "异型")),
    ("pan-luodi-gangguan-24", ("落地",)),
)

_CMP_CHAIN_RE = re.compile(
    r"^(-?\d+(?:\.\d+)?|[A-Za-z_]\w*)\s*"
    r"(<=|>=|<|>|==|!=)\s*"
    r"(-?\d+(?:\.\d+)?|[A-Za-z_]\w*)"
    r"(?:\s*(<=|>=|<|>|==|!=)\s*(-?\d+(?:\.\d+)?|[A-Za-z_]\w*))?$")
_IDENT_RE = re.compile(r"^[A-Za-z_]\w*$")
_NUM_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


def load_panorama(data_dir=None):
    """加载危大阈值清单并做结构校验；不可用 → KnowledgeError（CLI exit 2）。"""
    base = find_data_dir(data_dir)
    if base is None:
        raise KnowledgeError(
            "未找到数据目录（含 knowledge/clauses）：可用 --data-dir 指定或设 SFC_DATA")
    path = os.path.join(base, "knowledge", "clauses", "panorama.json")
    if not os.path.isfile(path):
        raise KnowledgeError("危大阈值清单缺失：%s" % path)
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except ValueError as exc:
        raise KnowledgeError("危大阈值清单 JSON 解析失败 %s：%s" % (path, exc))
    items = doc.get("items")
    if not isinstance(items, list) or not items:
        raise KnowledgeError("危大阈值清单结构坏：items 缺失或为空")
    for item in items:
        for key in ("item_id", "project_type", "judge_params", "levels", "basis"):
            if key not in item:
                raise KnowledgeError("危大条目缺 %s：%r" % (key, item.get("item_id")))
        for level in (LEVEL_NONE, LEVEL_WEIDA, LEVEL_CHAOGUIMO):
            if level not in item["levels"]:
                raise KnowledgeError("危大条目缺级别 %s：%s"
                                     % (level, item["item_id"]))
    return doc


def recognize_item(project_type):
    """工程类型识别：project_type 文本 → 清单条目 id；未识别返回 None。"""
    text = project_type or ""
    for item_id, keywords in _TYPE_KEYWORDS:
        if any(k in text for k in keywords):
            return item_id
    return None


def _resolve_operand(token, params):
    """操作数求值：数字 → float；参数名 → 取值（缺失 → None）。"""
    token = token.strip()
    if _NUM_RE.match(token):
        return float(token)
    if token not in params or params[token] is None:
        return None
    value = params[token]
    if isinstance(value, bool):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _cmp(left, op, right):
    if op == "<=":
        return left <= right
    if op == ">=":
        return left >= right
    if op == "<":
        return left < right
    if op == ">":
        return left > right
    if op == "==":
        return left == right
    if op == "!=":
        return left != right
    raise KnowledgeError("不支持的条件比较符 %r" % (op,))


def _eval_atom(atom, params):
    """单原子求值（三值逻辑）：True/False/None（None=参数缺失）。"""
    a = atom.strip()
    if a.startswith("!"):
        inner = a[1:].strip()
        if inner.startswith("(") and inner.endswith(")"):
            inner = inner[1:-1].strip()
        value = _eval_atom(inner, params)
        return None if value is None else (not value)
    if a in ("true", "True"):
        return True
    if a in ("false", "False"):
        return False
    m = _CMP_CHAIN_RE.match(a)
    if m:
        operands = [m.group(1), m.group(3)]
        ops = [m.group(2)]
        if m.group(4):
            operands.append(m.group(5))
            ops.append(m.group(4))
        values = [_resolve_operand(t, params) for t in operands]
        if any(v is None for v in values):
            return None
        ok = True
        for i, op in enumerate(ops):
            left, right = values[i], values[i + 1]
            if isinstance(left, bool) or isinstance(right, bool):
                return None  # 布尔参数不参与数值比较（清单数据无此形态，防御性）
            ok = ok and _cmp(left, op, right)
        return ok
    if _IDENT_RE.match(a):
        if a not in params or params[a] is None:
            return None
        return bool(params[a])
    raise KnowledgeError("无法解析分级条件原子 %r" % (a,))


def _eval_and(part, params):
    results = [_eval_atom(a, params) for a in part.split("&&")]
    if False in results:
        return False
    if all(r is True for r in results):
        return True
    return None


def eval_cond(cond, params):
    """清单条件表达式求值：|| / && / ! / 比较链 / 布尔参数，三值逻辑。"""
    c = cond.strip()
    if c.startswith("false"):
        return False
    if c.startswith("true"):
        return True
    results = [_eval_and(p, params) for p in c.split("||")]
    if True in results:
        return True
    if all(r is False for r in results):
        return False
    return None


def _pending(note, item_id=None, unknown_params=None, project_type=None):
    return {
        "status": "pending",
        "item_id": item_id,
        "project_type": project_type,
        "note": note,
        "unknown_params": list(unknown_params or []),
    }


def judge(item_id, params, panorama=None):
    """对已识别条目逐级判定（none→weida→chaoguimo，首个 True 生效）。

    params 缺失条件参数 → pending（待人工确认），不猜值。
    """
    doc = panorama or load_panorama()
    item = None
    for it in doc["items"]:
        if it["item_id"] == item_id:
            item = it
            break
    if item is None:
        return _pending("清单条目不存在：%s" % item_id)
    if not all(b.get("status") == "已核对" for b in item["basis"]):
        return _pending("分级依据待核对，暂不出确定结论", item_id=item_id,
                        project_type=item["project_type"])
    unknown = [k for k in item["judge_params"]
               if k not in params or params[k] is None]
    levels = item["levels"]
    results = {}
    for level in (LEVEL_NONE, LEVEL_WEIDA, LEVEL_CHAOGUIMO):
        results[level] = eval_cond(levels[level]["cond"], params)
    # 超规模条件成立时危大条件必然成立（阈值更低），故从最高级向下取首个 True
    for level in (LEVEL_CHAOGUIMO, LEVEL_WEIDA, LEVEL_NONE):
        if results[level] is True:
            return _definite(item, level, params)
    if any(r is None for r in results.values()):
        return _pending("分级参数缺失，待人工确认：%s" % (", ".join(unknown) or "条件含未解析参数"),
                        item_id=item_id, unknown_params=unknown,
                        project_type=item["project_type"])
    return _pending("清单条件未覆盖当前取值（条件全为假）", item_id=item_id,
                    project_type=item["project_type"])


def _definite(item, level, params):
    level_def = item["levels"][level]
    primary = item["judge_params"][0] if item["judge_params"] else None
    return {
        "status": "definite",
        "item_id": item["item_id"],
        "project_type": item["project_type"],
        "level": level,
        "label": level_def["label"],
        "duty": level_def.get("duty"),
        "cond": level_def["cond"],
        "rule_id": _RULE_ID_SPECIAL.get((item["item_id"], level), "G-" + item["item_id"]),
        "verdict": "pass" if level == LEVEL_NONE else "triggered",
        "param": primary,
        "actual": params.get(primary) if primary else None,
        "basis": [{"doc": b.get("doc"), "excerpt": b.get("excerpt")}
                  for b in item["basis"]],
        "note": item.get("note"),
    }


def judge_card(scheme_card, panorama=None, param_overrides=None):
    """从方案卡判级：类型识别 → 卡内条目值 + 显式覆盖 → judge。"""
    params = {}
    for name, entry in scheme_card.entries.items():
        value = entry.get("value")
        if isinstance(value, (int, float, bool)):
            params[name] = value
    for key, value in (param_overrides or {}).items():
        params[key] = value
    item_id = recognize_item(scheme_card.project_type)
    if item_id is None:
        return _pending("工程类型未识别（无法匹配危大清单条目）",
                        project_type=scheme_card.project_type)
    return judge(item_id, params, panorama=panorama)


__all__ = [
    "eval_cond", "judge", "judge_card", "load_panorama", "recognize_item",
]
