# -*- coding: utf-8 -*-
"""危大分级页（plan/04 §8 页签 4）：方案文件 + 可选参数覆盖 → 判定卡。

只消费 grading.judge_card（三值条件求值器，不 eval）；pending=参数缺失
待人工确认，不硬判——与 CLI 同口径。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit,
    QVBoxLayout, QWidget,
)

from . import pipelines
from .pipelines import KnowledgeError, ParseError

_LEVEL_TEXT = {"none": "非危大工程", "weida": "危大工程",
               "chaoguimo": "超过一定规模的危大工程"}


class GradingTab(QWidget):
    notify = Signal(str)

    def __init__(self, data_dir_getter, parent=None):
        super().__init__(parent)
        self._get_data_dir = data_dir_getter
        self.result = None

        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("专项施工方案文件（.docx/.pdf）")
        browse = QPushButton("选择文件…")
        browse.clicked.connect(self._on_browse)
        self.param_edit = QLineEdit()
        self.param_edit.setPlaceholderText("参数覆盖（可空；格式 name=value，分号分隔，如 build_height=56）")
        self.run_button = QPushButton("分级判定")
        self.run_button.clicked.connect(self._on_run)

        self.summary_label = QLabel("判定方案所属危大清单条目与级别（结论/义务/依据摘录）。")
        self.summary_label.setWordWrap(True)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)

        file_row = QHBoxLayout()
        file_row.addWidget(self.file_edit, 1)
        file_row.addWidget(browse)
        layout = QVBoxLayout(self)
        layout.addLayout(file_row)
        layout.addWidget(self.param_edit)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.run_button)
        layout.addLayout(buttons)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.detail, 1)

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择专项施工方案", "", "方案文件 (*.docx *.pdf)")
        if path:
            self.file_edit.setText(path)

    def scheme_path(self):
        return self.file_edit.text().strip()

    def set_scheme_path(self, path):
        self.file_edit.setText(path)

    def parse_overrides(self):
        """参数覆盖文本 → dict（bad 形式抛 ValueError，消息面向用户）。"""
        text = self.param_edit.text().strip()
        if not text:
            return {}
        overrides = {}
        for item in text.split(";"):
            item = item.strip()
            if not item:
                continue
            name, sep, value = item.partition("=")
            if not sep or not name.strip():
                raise ValueError("参数覆盖须为 name=value 形式（分号分隔），得到 %r" % item)
            v = value.strip()
            if v.lower() == "true":
                overrides[name.strip()] = True
            elif v.lower() == "false":
                overrides[name.strip()] = False
            else:
                try:
                    overrides[name.strip()] = float(v)
                except ValueError:
                    overrides[name.strip()] = v
        return overrides

    # ---- 业务（引擎 API）----

    def run_grading(self):
        """分级管线：ParseError/KnowledgeError/ValueError 向上抛。"""
        self.result = pipelines.run_grading_pipeline(
            self.scheme_path(), overrides=self.parse_overrides(),
            data_dir=self._get_data_dir())
        return self.result

    # ---- 槽 ----

    def _on_run(self):
        if not self.scheme_path():
            self.notify.emit("请先选择方案文件。")
            return
        try:
            result = self.run_grading()
        except (ParseError, KnowledgeError, ValueError) as exc:
            self.notify.emit("分级判定未执行：%s" % exc)
            return
        self.show_result(result)
        self.notify.emit("分级判定完成：%s"
                         % (result.get("label") or result.get("note") or result.get("status")))

    def show_result(self, result):
        if result.get("status") == "definite":
            head = "结论：%s（%s）\n判定条件：%s\n义务：%s" % (
                _LEVEL_TEXT.get(result.get("level"), result.get("level")),
                result.get("rule_id"), result.get("cond"), result.get("duty"))
        else:
            head = "结论：待人工确认\n原因：%s" % result.get("note")
            if result.get("unknown_params"):
                head += "\n缺失参数：%s" % "、".join(result["unknown_params"])
        lines = [head, "工程类型：%s（条目 %s）"
                 % (result.get("project_type") or "未识别", result.get("item_id") or "-")]
        basis = result.get("basis") or []
        if basis:
            lines.append("依据摘录：")
            for b in basis:
                lines.append("  · %s：%s" % (b.get("doc"), b.get("excerpt")))
        self.summary_label.setText(lines[0])
        self.detail.setPlainText("\n".join(lines))
        self.result = result
