# -*- coding: utf-8 -*-
"""M3 参数卡（方案卡/验算书卡）：统一 schema（plan/04 §1）。

与引擎输入卡（engine/card.py，扁平键）不同：方案卡/验算书卡按条目制组织
entries[name] = {value, unit, confidence, evidence}，供核查规则/一致性/分级消费。

- 置信度 < CONFIDENCE_MIN 或取值缺失的槽位进 unknown_slots（宁缺勿错，
  后续核查跳过该槽位记"待人工确认"，而非硬判——plan/04 §1）；
- evidence 登记 locator/quote，报告可回溯到原文位置。
"""

CONFIDENCE_MIN = 0.7

CATEGORY_COUPLE = "coupler_steel_pipe_scaffold"
CATEGORY_FORMWORK = "formwork_support"


class ParseError(Exception):
    """方案文档不可解析（缺文件/坏格式/依赖缺失）。按输入不可用处置（CLI exit 2）。"""


class SchemeCard(object):
    """方案参数卡 / 验算书取值卡（同一 schema，card_type 区分）。"""

    def __init__(self, card_type, doc_name=None):
        if card_type not in ("scheme", "calcbook"):
            raise ValueError("card_type 须为 scheme/calcbook，得到 %r" % (card_type,))
        self.card_type = card_type
        self.doc_name = doc_name
        self.category = None      # coupler_steel_pipe_scaffold / formwork_support / None
        self.project_type = ""    # 工程类型描述文本（only_if 门控与分级类型识别的匹配对象）
        self.entries = {}         # name -> {"value","unit","confidence","evidence"}
        self.unknown_slots = []   # 宁缺槽位（解析失败/低置信度）

    def set(self, name, value, unit=None, confidence=1.0, evidence=None):
        """登记槽位；取值缺失或置信度不足时转 unknown_slots（返回 False）。"""
        if value is None or confidence < CONFIDENCE_MIN:
            if name not in self.unknown_slots:
                self.unknown_slots.append(name)
            self.entries.pop(name, None)
            return False
        self.entries[name] = {
            "value": value,
            "unit": unit,
            "confidence": confidence,
            "evidence": evidence or {},
        }
        if name in self.unknown_slots:
            self.unknown_slots.remove(name)
        return True

    def is_known(self, name):
        return name in self.entries

    def value(self, name, default=None):
        entry = self.entries.get(name)
        return default if entry is None else entry["value"]

    def confidence_of(self, name):
        entry = self.entries.get(name)
        return None if entry is None else entry["confidence"]

    def to_dict(self):
        return {
            "card_type": self.card_type,
            "doc_name": self.doc_name,
            "category": self.category,
            "project_type": self.project_type,
            "entries": {k: dict(v) for k, v in self.entries.items()},
            "unknown_slots": list(self.unknown_slots),
        }
