# -*- coding: utf-8 -*-
"""M4 报告测试共用断言（docx zip 结构检查）。"""

import re
import zipfile


def read_plain_text(path):
    """docx → 主文档纯文本（去 XML 标签），供内容断言。"""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    return re.sub(r"<[^>]+>", "", xml)


def assert_no_external_links(path):
    """DoD ②：docx 内全部 .rels 无 TargetMode="External"（0 外链断言）。"""
    with zipfile.ZipFile(path) as z:
        rels = [n for n in z.namelist() if n.endswith(".rels")]
        assert rels, "docx 应含关系文件"
        for name in rels:
            assert b'TargetMode="External"' not in z.read(name), name


def assert_no_timestamps(path):
    """DoD ③：zip 全条目固定时间戳 + core.xml/app.xml 固定内容。"""
    with zipfile.ZipFile(path) as z:
        for zi in z.infolist():
            assert zi.date_time == (1980, 1, 1, 0, 0, 0), (path, zi.filename)
        core = z.read("docProps/core.xml")
        assert b"sfc-report" in core
        assert b"2026-01-01T00:00:00Z" in core
        assert b"2026-10" not in core
