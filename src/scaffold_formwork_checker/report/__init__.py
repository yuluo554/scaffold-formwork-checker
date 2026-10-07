# -*- coding: utf-8 -*-
"""M4 报告导出（report/，plan/04 §7）。

- generate_calc_report：参数卡 + CalcResult → docx 验算书（calc_report.py）；
- generate_check_report：run_checks 报告 → docx 核查报告（check_report.py）。

确定性纪律（DoD ②③）：内容无时间戳（签署栏手填）、零外链（docx 内无
TargetMode="External" 超链关系）、落盘 zip 规范化（同输入位级一致）；
免责声明为强制节。测试锁死：tests/test_report_calc.py、tests/test_report_check.py。
"""

from .calc_report import generate_calc_report
from .check_report import generate_check_report
from .docx_writer import (
    DISCLAIMER, TOOL_LINE, add_table, fmt_num, fmt_num4, fmt_value,
    new_document, normalize_docx_bytes, save_normalized,
)

__all__ = [
    "DISCLAIMER", "TOOL_LINE", "add_table", "fmt_num", "fmt_num4", "fmt_value",
    "generate_calc_report", "generate_check_report", "new_document",
    "normalize_docx_bytes", "save_normalized",
]
