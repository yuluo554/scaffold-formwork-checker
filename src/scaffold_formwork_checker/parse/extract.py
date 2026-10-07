# -*- coding: utf-8 -*-
"""M3 文本抽取管线：docx/pdf 文本 → 方案卡 + 验算书卡（确定性规则，零 LLM）。

抽取策略（置信度分层，< CONFIDENCE_MIN 自动进 unknown_slots）：
1. 工程类型/类别：标题行识别（only_if 门控与分级类型识别共用匹配文本）；
2. 搭设参数表：表头含"参数/取值"的表格逐行标签匹配（置信度 0.99）；
3. 正文正则：搭设高度等（置信度 0.85；同槽多个不同值 → 0.5 降级 unknown_slots）；
4. 关键词在位：剪刀撑/专家论证/专项施工方案（置信度 0.85，命中与缺失同权——
   文本路线固有局限：图片表格/扫描件读不到，属 README 已登记限制）；
5. 验算书卡："验算取值"句式 → 步距/纵距/横距（置信度 0.85）。
"""

import re

from .card import (
    CATEGORY_COUPLE,
    CATEGORY_FORMWORK,
    SchemeCard,
)

CONF_TABLE = 0.99      # 参数表逐行匹配
CONF_TEXT = 0.85       # 正文正则/关键词在位
CONF_AMBIGUOUS = 0.5   # 同槽多值冲突 → 强制进 unknown_slots

_TITLE_SUFFIX = "专项施工方案"

_HEIGHT_RE = re.compile(r"搭设高度\s*([0-9]+(?:\.[0-9]+)?)\s*m")
_ROWS_RE = re.compile(r"[（(](单排|双排)[）)]")
_SECTION_RE = re.compile(r"^[一二三四五六七八九十]+\s*、")
# 搭设高度只从这些章节提取：构造措施等章节的模板句（如"24m及以上（若适用）"）
# 不是实际搭设高度声明，纳入会误伤（多值冲突降级）
_HEIGHT_SECTION_KEYS = ("工程概况", "危大工程管理")
_CALCBOOK_RE = re.compile(
    r"验算取值[：:]?\s*步距\s*([0-9]+(?:\.[0-9]+)?)\s*m\s*[，,]\s*"
    r"立杆纵距\s*([0-9]+(?:\.[0-9]+)?)\s*m\s*[，,]\s*"
    r"立杆横距\s*([0-9]+(?:\.[0-9]+)?)\s*m")

_LENGTH_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*m")
_PIPE_RE = re.compile(r"48\.3\s*[×xX]\s*3\.6")
_BOARD_RE = re.compile(r"铺\s*([0-9]+)\s*层")
_LIVE_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*kN/m")

_WALL_TIE_ENUM = {"两步三跨": "two_step_three_span", "三步三跨": "three_step_three_span"}

# 参数表标签 → (槽位, 取值解析器, 单位)。顺序即匹配顺序（标签互不重叠）。
_TABLE_LABELS = (
    ("cross_spacing", ("横距",), "m"),
    ("long_spacing", ("纵距",), "m"),
    ("step", ("步距",), "m"),
    ("wall_tie_v", ("竖向间距",), "m"),
    ("wall_tie_h", ("水平间距",), "m"),
    ("wall_tie", ("连墙件布置",), None),
    ("pipe_spec", ("钢管规格",), None),
    ("board_layers", ("脚手板",), None),
    ("live_load", ("施工荷载",), None),
)
_TABLE_SLOTS = {name: unit for name, _, unit in _TABLE_LABELS}


def _parse_length(text):
    m = _LENGTH_RE.search(text)
    return float(m.group(1)) if m else None


def _parse_wall_tie(text):
    for cn, enum in _WALL_TIE_ENUM.items():
        if cn in text:
            return enum
    return None


def _parse_pipe(text):
    return "48.3x3.6" if _PIPE_RE.search(text) else None


def _parse_board(text):
    m = _BOARD_RE.search(text)
    return int(m.group(1)) if m else None


def _parse_live(text):
    m = _LIVE_RE.search(text)
    return float(m.group(1)) if m else None


_PARSERS = {
    "cross_spacing": _parse_length,
    "long_spacing": _parse_length,
    "step": _parse_length,
    "wall_tie_v": _parse_length,
    "wall_tie_h": _parse_length,
    "wall_tie": _parse_wall_tie,
    "pipe_spec": _parse_pipe,
    "board_layers": _parse_board,
    "live_load": _parse_live,
}


def _find_heading(paragraphs):
    """标题行：含"专项施工方案"的首段（门控/类型识别的匹配文本）。"""
    for p in paragraphs:
        if _TITLE_SUFFIX in p["text"]:
            return p["text"]
    return paragraphs[0]["text"] if paragraphs else ""


def _recognize_category(text):
    if ("模板支撑" in text) or ("模板支架" in text) or ("承重支撑" in text):
        return CATEGORY_FORMWORK
    if "脚手架" in text:
        return CATEGORY_COUPLE
    return None


def _params_table_rows(tables):
    """定位搭设参数表（表头含"参数"与"取值"），返回数据行列表。"""
    for table in tables:
        if not table:
            continue
        header = table[0]
        if (any("参数" in cell for cell in header)
                and any("取值" in cell for cell in header)):
            return [row for row in table[1:] if any(cell for cell in row)]
    return []


def _extract_table_params(card, tables):
    rows = _params_table_rows(tables)
    if not rows:
        return
    for row in rows:
        label = row[0]
        value_text = row[1] if len(row) > 1 else ""
        for name, keywords, unit in _TABLE_LABELS:
            if any(k in label for k in keywords):
                evidence = {"locator": "搭设参数表", "quote": "%s：%s" % (label, value_text)}
                card.set(name, _PARSERS[name](value_text), unit=unit,
                         confidence=CONF_TABLE, evidence=evidence)
                break


def _split_sections(lines):
    """按中文序号标题（"一、××"）切分章节，返回 [(章节标题, [正文行])]。

    无章节结构的文档整体归入（卷首），此时搭设高度回退全文提取。
    """
    sections = []
    title, body = "（卷首）", []
    for line in lines:
        if _SECTION_RE.match(line):
            if body:
                sections.append((title, body))
            title, body = line, []
        else:
            body.append(line)
    if body:
        sections.append((title, body))
    return sections


def _extract_build_height(card, sections):
    pool = []
    for title, lines in sections:
        if any(k in title for k in _HEIGHT_SECTION_KEYS):
            pool.extend(lines)
    if not pool:
        for _, lines in sections:
            pool.extend(lines)
    values = []
    quotes = []
    for line in pool:
        for m in _HEIGHT_RE.finditer(line):
            values.append(float(m.group(1)))
            quotes.append(line)
    if not values:
        card.set("build_height", None, unit="m", confidence=CONF_TEXT,
                 evidence={"locator": "正文", "quote": "正文未找到搭设高度"})
        return
    distinct = sorted(set(values))
    if len(distinct) > 1:
        # 多值冲突：宁可缺勿错 → 降级进 unknown_slots（待人工确认）
        card.set("build_height", None, unit="m", confidence=CONF_AMBIGUOUS,
                 evidence={"locator": "正文", "quote": "搭设高度多值冲突：%s"
                           % ", ".join("%.2f" % v for v in distinct)})
        return
    card.set("build_height", distinct[0], unit="m", confidence=CONF_TEXT,
             evidence={"locator": "正文", "quote": quotes[0]})


def _extract_keywords(card, lines, heading):
    """关键词在位类槽位：命中/缺失同权登记（文本路线在位性判定）。"""
    body = [line for line in lines if line != heading]
    keywords = (
        ("scissor_brace", "剪刀撑", "剪刀撑设置措施"),
        ("expert_review", "专家论证", "专家论证安排"),
        ("special_plan", "专项施工方案", "专项施工方案编制安排"),
    )
    for name, keyword, label in keywords:
        hits = [line for line in body if keyword in line]
        quote = hits[0] if hits else "正文未提及%s（%s）" % (label, keyword)
        card.set(name, bool(hits), unit=None, confidence=CONF_TEXT,
                 evidence={"locator": "全文关键词", "quote": quote})


def extract_scheme(doc, doc_name=""):
    """文档模型 → 方案卡（plan/04 §1 schema）。"""
    card = SchemeCard("scheme", doc_name=doc_name)
    paragraphs = doc.get("paragraphs", [])
    tables = doc.get("tables", [])
    lines = [p["text"] for p in paragraphs]
    if not lines:
        card.project_type = ""
        card.set("build_height", None, unit="m", confidence=CONF_TEXT,
                 evidence={"locator": "正文", "quote": "文档无文本"})
        return card
    heading = _find_heading(paragraphs)
    card.project_type = heading
    card.category = _recognize_category(heading)
    m = _ROWS_RE.search("\n".join(lines))
    if m:
        card.set("rows", "double" if m.group(1) == "双排" else "single",
                 unit=None, confidence=CONF_TEXT,
                 evidence={"locator": "工程概况", "quote": m.group(0)})
    else:
        card.set("rows", None, unit=None, confidence=CONF_TEXT,
                 evidence={"locator": "工程概况", "quote": "未识别单排/双排"})
    _extract_table_params(card, tables)
    _extract_build_height(card, _split_sections(lines))
    _extract_keywords(card, lines, heading)
    # 收尾：参数表槽位未被填且未登记的（表缺失/缺行）显式转 unknown_slots——
    # 宁缺槽位清单必须完整（后续核查跳过并记待人工确认，而非当作无此槽）
    for name, unit in _TABLE_SLOTS.items():
        if not card.is_known(name) and name not in card.unknown_slots:
            card.set(name, None, unit=unit, confidence=CONF_TABLE,
                     evidence={"locator": "搭设参数表",
                               "quote": "参数表未找到或未含该行"})
    return card


def extract_calcbook(doc, doc_name="", scheme_card=None):
    """文档模型 → 验算书取值卡（与方案卡同 schema，card_type=calcbook）。"""
    card = SchemeCard("calcbook", doc_name=doc_name)
    if scheme_card is not None:
        card.category = scheme_card.category
        card.project_type = scheme_card.project_type
    for line in (p["text"] for p in doc.get("paragraphs", [])):
        m = _CALCBOOK_RE.search(line)
        if not m:
            continue
        evidence = {"locator": "验算书章节", "quote": line}
        card.set("step", float(m.group(1)), unit="m", confidence=CONF_TEXT, evidence=evidence)
        card.set("long_spacing", float(m.group(2)), unit="m", confidence=CONF_TEXT, evidence=evidence)
        card.set("cross_spacing", float(m.group(3)), unit="m", confidence=CONF_TEXT, evidence=evidence)
        return card
    for name in ("step", "long_spacing", "cross_spacing"):
        card.set(name, None, unit="m", confidence=CONF_TEXT,
                 evidence={"locator": "验算书章节", "quote": "未找到验算取值句式"})
    return card


def extract_document(doc, doc_name=""):
    """文档模型 → (方案卡, 验算书卡)。"""
    scheme = extract_scheme(doc, doc_name=doc_name)
    calcbook = extract_calcbook(doc, doc_name=doc_name, scheme_card=scheme)
    return scheme, calcbook
