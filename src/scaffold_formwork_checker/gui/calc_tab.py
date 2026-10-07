# -*- coding: utf-8 -*-
"""验算页（plan/04 §8 页签 1）：模块选择 → 动态参数卡表单 → 结果表 → 导出。

Qt 表现层：字段规格来自 gui/specs.py，验算与导出走 gui/pipelines.py
（引擎 API），本模块不含任何判定逻辑。通知走 notify 信号（非模态）。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from ..engine import CardError, KnowledgeError
from . import pipelines, specs

_VERDICT_TEXT = {"pass": "通过", "fail": "不通过"}


def _fmt_detail(value):
    """中间量展示 4 位小数（与报告层 fmt_num4 同口径，纯展示不进计算）。"""
    if isinstance(value, float):
        return ("%.4f" % value).rstrip("0").rstrip(".")
    return str(value)


class CalcTab(QWidget):
    notify = Signal(str)

    def __init__(self, data_dir_getter, parent=None):
        super().__init__(parent)
        self._get_data_dir = data_dir_getter
        self._fields = {}
        self.result = None
        self.card_data = None

        self.module_combo = QComboBox()
        for mid in specs.MODULE_NAMES:
            self.module_combo.addItem("%s  %s" % (mid, specs.MODULE_NAMES[mid]), mid)
        self.module_label = QLabel()
        self.module_combo.currentIndexChanged.connect(self._on_module_changed)

        self.form_host = QWidget()
        self.form = QFormLayout(self.form_host)
        self.form.setLabelAlignment(Qt.AlignRight)
        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setWidget(self.form_host)

        self.run_button = QPushButton("验算")
        self.run_button.clicked.connect(self._on_run)
        self.export_button = QPushButton("导出验算书…")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._on_export)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.run_button)
        buttons.addWidget(self.export_button)

        self.summary_label = QLabel("填写参数后点击“验算”。默认参数转录自带真值算例，可直接运行。")
        self.summary_label.setWordWrap(True)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["检查项", "表达式", "代入", "比值", "限值", "结论", "条款号"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("验算模块："))
        top.addWidget(self.module_combo, 1)
        layout.addLayout(top)
        layout.addWidget(form_scroll, 3)
        layout.addLayout(buttons)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.table, 4)

        self._on_module_changed()

    # ---- 表单 ----

    def _on_module_changed(self, *_):
        mid = self.current_module()
        self.module_label.setText(specs.MODULE_NAMES[mid])
        while self.form.count():
            item = self.form.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._fields = {}
        for path, label, kind, unit, options in specs.FIELD_SPECS[mid]:
            edit = QLineEdit()
            edit.setText(specs.default_text(mid, path, kind))
            if kind == "enum":
                box = QComboBox()
                for value, text in options:
                    box.addItem(text, value)
                current = specs.default_text(mid, path, kind)
                idx = box.findData(current)
                if idx >= 0:
                    box.setCurrentIndex(idx)
                box.currentIndexChanged.connect(
                    lambda _=None, b=box, p=path: self._fields.__setitem__(p, b.currentData()))
                self._fields[path] = box.currentData()
                edit.deleteLater()
                widget = box
            else:
                self._fields[path] = edit
                widget = edit
            caption = label + ("（%s）" % unit if unit else "")
            self.form.addRow(caption, widget)
        self.result = None
        self.export_button.setEnabled(False)
        self.table.setRowCount(0)
        self.summary_label.setText("参数已重置为默认卡（%s）。" % mid)

    def current_module(self):
        return self.module_combo.currentData()

    def collect_values(self):
        """当前表单取值 {path: 文本}（enum 已存枚举值）。"""
        values = {}
        for path, widget in self._fields.items():
            values[path] = widget if isinstance(widget, str) else widget.text()
        return values

    def build_card(self):
        """表单 → 参数卡 dict（转换失败抛 CardError，消息面向用户）。"""
        return specs.assemble(self.current_module(), self.collect_values())

    # ---- 业务（引擎 API）----

    def run_calc(self):
        """验算管线：参数卡 → CalcResult。CardError/KnowledgeError 向上抛。"""
        card = self.build_card()
        self.card_data = card
        self.result = pipelines.run_calc_pipeline(
            card, module_id=self.current_module(), data_dir=self._get_data_dir())
        return self.result

    # ---- 槽 ----

    def _on_run(self):
        try:
            result = self.run_calc()
        except (CardError, KnowledgeError) as exc:
            self.notify.emit("验算未执行：%s" % exc)
            return
        self.show_result(result)
        self.notify.emit("验算完成：%s（%d 项检查）"
                         % (result.get("module_id"), len(result.get("checks", []))))

    def show_result(self, result):
        status = result.get("status")
        if status == "blocked":
            self.summary_label.setText(
                "不可验算（依据未核对）：%s\n验算书导出仅载说明。"
                % result.get("status_note", ""))
            self.table.setRowCount(0)
            self.result = result
            self.export_button.setEnabled(True)
            return
        rows = result.get("checks", [])
        self.table.setRowCount(len(rows))
        for i, chk in enumerate(rows):
            ratio = "%.4f" % chk["ratio"] if chk.get("ratio") is not None else ""
            values = [
                chk.get("item"), chk.get("expr"), chk.get("substituted"),
                ratio, chk.get("limit"), _VERDICT_TEXT.get(chk.get("verdict"), chk.get("verdict")),
                "、".join(chk.get("clause_refs") or []),
            ]
            for j, text in enumerate(values):
                item = QTableWidgetItem("" if text is None else str(text))
                if j == 5 and chk.get("verdict") != "pass":
                    item.setForeground(Qt.red)
                self.table.setItem(i, j, item)
        fails = sum(1 for c in rows if c.get("verdict") != "pass")
        summary = "%s：%d 项检查，%d 项不通过。" % (
            specs.MODULE_NAMES.get(result.get("module_id"), result.get("module_id")),
            len(rows), fails)
        detail = result.get("detail") or {}
        if detail:
            summary += "  中间量：" + "；".join(
                "%s=%s" % (k, _fmt_detail(v)) for k, v in sorted(detail.items()))
        self.summary_label.setText(summary)
        self.result = result
        self.export_button.setEnabled(True)

    def _on_export(self):
        if self.result is None:
            self.notify.emit("尚未验算，无可导出结果。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出验算书", "验算书.docx", "Word 文档 (*.docx)")
        if not path:
            return
        try:
            pipelines.export_calc_report(self.card_data, self.result, path)
        except (CardError, KnowledgeError, OSError) as exc:
            self.notify.emit("导出失败：%s" % exc)
            return
        self.notify.emit("验算书已导出：%s" % path)
