"""scaffold-formwork-checker：脚手架与模板支架安全验算及危大分级工具。

规划见 plan/（00 总览、03 架构、04 模块详设）。核心纪律：数值结论永远来自
确定性规则，未经原文核对（status=待核对）的条文数值不得进入计算路径。

v2.0.0（2026-10-19）：Python floor >=3.10；条款库带复核元数据（meta.review，
见 tests/test_clause_review.py 守门）。
v2.0.1（2026-10-24）：条款 `JGJ162-4.1.1` 的 formula_refs 拆分（未核对引用移入
pending_formula_refs），并重建发布物——v2.0.0 的 exe 内嵌的是改动前的条款库。
"""

__version__ = "2.0.1"

__all__ = ["__version__"]
