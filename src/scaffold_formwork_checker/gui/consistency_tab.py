# -*- coding: utf-8 -*-
"""一致性页（plan/04 §8 页签 3）：方案文件（+可选验算书文件）→ 两卡差异表。

两张皮口径与 CLI 同源（consistency.check_rule）：超容差即 violation，
方向只定级别（劣于=不合格/优于=提示）；任一侧缺字段=待人工确认。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from . import pipelines
from .pipelines import ChecksError, KnowledgeError, ParseError

_VERDICT_TEXT = {"pass": "一致", "violation": "不一致"}


class ConsistencyTab(QWidget):
    notify = Signal(str)

    def __init__(self, data_dir_getter, parent=None):
        super().__init__(parent)
        self._get_data_dir = data_dir_getter
        self.outcome = None

        self.scheme_edit = QLineEdit()
        self.scheme_edit.setPlaceholderText("方案文件（.docx/.pdf，必选）")
        self.calcbook_edit = QLineEdit()
        self.calcbook_edit.setPlaceholderText("验算书文件（可选；缺省用方案内验算书章节）")
        browse_a = QPushButton("选择方案…")
        browse_a.clicked.connect(self._on_browse_scheme)
        browse_b = QPushButton("选择验算书…")
        browse_b.clicked.connect(self._on_browse_calcbook)

        self.run_button = QPushButton("比对")
        self.run_button.clicked.connect(self._on_run)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.run_button)

        self.summary_label = QLabel("比对方案参数卡与验算书取值卡（同一 schema 字段对齐）。")
        self.summary_label.setWordWrap(True)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["规则", "参数", "方案取值", "验算书取值", "差值", "容差", "结论", "影响/说明"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        grid = QVBoxLayout()
        row_a = QHBoxLayout()
        row_a.addWidget(self.scheme_edit, 1)
        row_a.addWidget(browse_a)
        row_b = QHBoxLayout()
        row_b.addWidget(self.calcbook_edit, 1)
        row_b.addWidget(browse_b)
        grid.addLayout(row_a)
        grid.addLayout(row_b)

        layout = QVBoxLayout(self)
        layout.addLayout(grid)
        layout.addLayout(buttons)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.table, 1)

    def _on_browse_scheme(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择方案文件", "", "方案文件 (*.docx *.pdf)")
        if path:
            self.scheme_edit.setText(path)

    def _on_browse_calcbook(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择验算书文件", "", "验算书文件 (*.docx *.pdf)")
        if path:
            self.calcbook_edit.setText(path)

    def set_paths(self, path_a, path_b=None):
        self.scheme_edit.setText(path_a)
        self.calcbook_edit.setText(path_b or "")

    # ---- 业务（引擎 API）----

    def run_consistency(self):
        """比对管线：ParseError/KnowledgeError/ChecksError 向上抛。"""
        path_a = self.scheme_edit.text().strip()
        path_b = self.calcbook_edit.text().strip() or None
        self.outcome = pipelines.run_consistency_pipeline(
            path_a, path_b, data_dir=self._get_data_dir())
        return self.outcome

    # ---- 槽 ----

    def _on_run(self):
        if not self.scheme_edit.text().strip():
            self.notify.emit("请先选择方案文件。")
            return
        try:
            outcome = self.run_consistency()
        except (ParseError, KnowledgeError, ChecksError) as exc:
            self.notify.emit("比对未执行：%s" % exc)
            return
        self.show_outcome(outcome)
        self.notify.emit("比对完成：%d 项不一致、%d 项待人工确认"
                         % (sum(1 for f in outcome["findings"]
                                if f.get("verdict") != "pass"),
                            len(outcome["confirmations"])))

    def show_outcome(self, outcome):
        rows = []
        for f in outcome.get("findings", []):
            rows.append((
                f.get("rule_id"), f.get("param"),
                f.get("scheme_value"), f.get("calcbook_value"),
                f.get("delta"), f.get("tolerance"),
                _VERDICT_TEXT.get(f.get("verdict"), f.get("verdict")),
                (f.get("impact") or f.get("note") or "")
                + ("｜%s" % f["expr"] if f.get("expr") else ""),
            ))
        for c in outcome.get("confirmations", []):
            rows.append((c.get("rule_id"), c.get("param"), None, None,
                         None, None, "待人工确认", c.get("reason")))
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, text in enumerate(row):
                if isinstance(text, float):
                    text = "%.4f" % text
                item = QTableWidgetItem("" if text is None else str(text))
                if j == 6 and text in ("不一致",):
                    item.setForeground(Qt.red)
                self.table.setItem(i, j, item)
        docs = "方案：%s" % outcome.get("scheme_doc")
        if outcome.get("calcbook_doc"):
            docs += "｜验算书：%s" % outcome["calcbook_doc"]
        self.summary_label.setText(docs)
        self.outcome = outcome
