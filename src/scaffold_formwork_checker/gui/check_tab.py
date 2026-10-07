# -*- coding: utf-8 -*-
"""方案核查页（plan/04 §8 页签 2）：文件选择 → 参数卡回显（unknown_slots
显式列出）→ 违规/待确认清单 → 导出核查报告。

只消费 gui/pipelines.py（引擎 API）；通知走 notify 信号（非模态）。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from . import pipelines
from .pipelines import ChecksError, KnowledgeError, ParseError

_VERDICT_TEXT = {"pass": "通过", "violation": "违规", "triggered": "触发（分级）"}


class CheckTab(QWidget):
    notify = Signal(str)

    def __init__(self, data_dir_getter, parent=None):
        super().__init__(parent)
        self._get_data_dir = data_dir_getter
        self.report = None

        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("专项施工方案文件（.docx / .pdf）")
        browse = QPushButton("选择文件…")
        browse.clicked.connect(self._on_browse)
        file_row = QHBoxLayout()
        file_row.addWidget(self.file_edit, 1)
        file_row.addWidget(browse)

        self.run_button = QPushButton("核查")
        self.run_button.clicked.connect(self._on_run)
        self.export_button = QPushButton("导出核查报告…")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._on_export)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.run_button)
        buttons.addWidget(self.export_button)

        self.summary_label = QLabel("选择方案文件后点击“核查”。")
        self.summary_label.setWordWrap(True)
        self.slots_label = QLabel("")
        self.slots_label.setWordWrap(True)
        self.slots_label.setVisible(False)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["规则", "检查项", "结论", "级别/说明", "要点", "条款号"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout = QVBoxLayout(self)
        layout.addLayout(file_row)
        layout.addLayout(buttons)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.slots_label)
        layout.addWidget(self.table, 1)

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择专项施工方案", "", "方案文件 (*.docx *.pdf)")
        if path:
            self.file_edit.setText(path)

    def scheme_path(self):
        return self.file_edit.text().strip()

    def set_scheme_path(self, path):
        self.file_edit.setText(path)

    # ---- 业务（引擎 API）----

    def run_check(self):
        """核查管线：ParseError/KnowledgeError/ChecksError 向上抛。"""
        self.report = pipelines.run_check_pipeline(
            self.scheme_path(), data_dir=self._get_data_dir())
        return self.report

    # ---- 槽 ----

    def _on_run(self):
        if not self.scheme_path():
            self.notify.emit("请先选择方案文件。")
            return
        try:
            report = self.run_check()
        except (ParseError, KnowledgeError, ChecksError) as exc:
            self.notify.emit("核查未执行：%s" % exc)
            return
        self.show_report(report)
        summary = report["summary"]
        self.notify.emit("核查完成：%d 项违规、%d 项待人工确认"
                         % (summary["violation"], summary["confirmations"]))

    def show_report(self, report):
        summary = report["summary"]
        self.summary_label.setText(
            "%s\n规则 %d 条，通过 %d、违规 %d、分级触发 %d、待人工确认 %d。"
            % (report.get("file"), summary["rules_total"], summary["pass"],
               summary["violation"], summary["triggered"], summary["confirmations"]))
        unknown = report.get("scheme_card", {}).get("unknown_slots") or []
        if unknown:
            self.slots_label.setText("待人工确认槽位（解析失败/低置信度，宁缺勿错）："
                                     + "、".join(unknown))
            self.slots_label.setVisible(True)
        else:
            self.slots_label.setVisible(False)
        rows = []
        for f in report.get("findings", []):
            rows.append((f.get("rule_id"), f.get("name"), _VERDICT_TEXT.get(f.get("verdict")),
                         f.get("level") or f.get("note"),
                         f.get("expr") or f.get("advice") or "",
                         "、".join(f.get("clause_refs") or [])))
        for c in report.get("confirmations", []):
            rows.append((c.get("rule_id"), c.get("name"), "待人工确认",
                         c.get("reason"), c.get("advice") or "",
                         "、".join(c.get("clause_refs") or [])))
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, text in enumerate(row):
                item = QTableWidgetItem("" if text is None else str(text))
                if j == 2 and text in ("违规",):
                    item.setForeground(Qt.red)
                self.table.setItem(i, j, item)
        self.report = report
        self.export_button.setEnabled(True)

    def _on_export(self):
        if self.report is None:
            self.notify.emit("尚未核查，无可导出报告。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出核查报告", "核查报告.docx", "Word 文档 (*.docx)")
        if not path:
            return
        try:
            pipelines.export_check_report(self.report, path,
                                          data_dir=self._get_data_dir())
        except (KnowledgeError, OSError) as exc:
            self.notify.emit("导出失败：%s" % exc)
            return
        self.notify.emit("核查报告已导出：%s" % path)
