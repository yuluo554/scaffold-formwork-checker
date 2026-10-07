# -*- coding: utf-8 -*-
"""M3 方案解析：docx/pdf → 参数卡（方案卡 + 验算书卡）。

文本路线零识图、零 LLM（plan/05 M3 产出口径）。低置信度/解析失败槽位
进 unknown_slots（宁缺勿错），后续核查跳过并记"待人工确认"而非硬判。
"""

import os

from .card import CONFIDENCE_MIN, ParseError, SchemeCard
from .docx_reader import read_docx
from .extract import extract_document
from .pdf_reader import read_pdf

_SUPPORTED_EXTS = (".docx", ".pdf")


class ParsedDocument(object):
    """解析产物：方案卡 + 验算书卡 + 告警（不致命的解析注意事项）。"""

    def __init__(self, scheme_card, calcbook_card, warnings=None):
        self.scheme_card = scheme_card
        self.calcbook_card = calcbook_card
        self.warnings = list(warnings or [])


def parse_document_text(paragraphs, tables, doc_name="", warnings=None):
    """从已抽取的文本（段落+表格）构建解析产物。

    供 pdf 文本路线与测试直接注入文本使用（tables 可为空——表格类参数
    将按 unknown_slots 处置）。
    """
    doc = {"paragraphs": paragraphs, "tables": tables or []}
    scheme, calcbook = extract_document(doc, doc_name=doc_name)
    return ParsedDocument(scheme, calcbook, warnings)


def parse_scheme(path):
    """按扩展名分发解析 docx/pdf。不支持的类型/读取失败 → ParseError。"""
    if not os.path.isfile(path):
        raise ParseError("方案文件不存在：%s" % path)
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        doc = read_docx(path)
    elif ext == ".pdf":
        doc = read_pdf(path)
        warning = ("PDF 文本路线无表格结构，参数表字段（步距/间距等）"
                   "以 unknown_slots 记待人工确认")
        parsed = parse_document_text(doc["paragraphs"], doc["tables"],
                                     doc_name=os.path.basename(path),
                                     warnings=[warning])
        return parsed
    else:
        raise ParseError(
            "不支持的方案文件类型 %r（支持 %s；.doc 旧格式请先另存为 .docx）"
            % (ext, "/".join(_SUPPORTED_EXTS)))
    return parse_document_text(doc["paragraphs"], doc["tables"],
                               doc_name=os.path.basename(path))


__all__ = [
    "CONFIDENCE_MIN", "ParseError", "ParsedDocument", "SchemeCard",
    "parse_scheme", "parse_document_text",
]
