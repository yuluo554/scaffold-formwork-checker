# -*- coding: utf-8 -*-
"""M3 pdf 读取器：pypdf 逐页抽文本（文本路线零识图）。

PDF 无表格结构：tables 恒空，表格类参数（步距/间距等）将进 unknown_slots
记"待人工确认"。真实 PDF 版式兼容性限制已在 README 登记。
"""

from .card import ParseError


def read_pdf(path):
    """读取 pdf → 段落列表（逐行）+ 空表格。pypdf 缺失/文件坏 → ParseError。"""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ParseError(
            "pypdf 未安装：请先 pip install \".[parse]\" 或 \".[dev]\"") from exc
    try:
        reader = PdfReader(path)
    except Exception as exc:
        raise ParseError("PDF 文件无法读取：%s" % exc) from exc
    lines = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        for line in text.splitlines():
            line = line.strip()
            if line:
                lines.append({"style": "", "text": line})
    return {"paragraphs": lines, "tables": []}
