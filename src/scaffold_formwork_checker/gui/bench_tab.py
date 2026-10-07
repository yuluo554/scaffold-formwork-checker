# -*- coding: utf-8 -*-
"""基准页（plan/04 §8 页签 5）：跑内置基准三套件 → 指标表（README 表同源）。

只消费 bench.run_all（零 API、离线、确定性）；门限=bench.BENCH_TARGETS。
运行为同步执行（秒级），按钮期间置忙态光标。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from .. import bench
from ..engine.loader import KnowledgeError
from . import pipelines

# 指标行定义与 bench.BENCH_TARGETS / README 基准表同源（_targets_met 口径）
_SUITE_ROWS = [
    ("examples", "算例真值回归（通过率）",
     lambda s: "%.1f%%" % (s["pass_rate"] * 100),
     lambda: "%.0f%%" % (bench.BENCH_TARGETS["examples_pass_rate"] * 100),
     lambda s: s["pass_rate"] >= bench.BENCH_TARGETS["examples_pass_rate"]),
    ("synthetic", "合成方案解析核查（F1）",
     lambda s: "%.4f" % s["metrics"]["f1"],
     lambda: "≥%.2f" % bench.BENCH_TARGETS["synthetic_f1_min"],
     lambda s: s["metrics"]["f1"] >= bench.BENCH_TARGETS["synthetic_f1_min"]),
    ("synthetic", "合成方案误报数",
     lambda s: str(s["metrics"]["false_positive_count"]),
     lambda: "≤%d" % bench.BENCH_TARGETS["synthetic_fp_max"],
     lambda s: s["metrics"]["false_positive_count"] <= bench.BENCH_TARGETS["synthetic_fp_max"]),
    ("grading", "分级边界值用例（通过率）",
     lambda s: "%.1f%%" % (s["pass_rate"] * 100),
     lambda: "%.0f%%" % (bench.BENCH_TARGETS["grading_pass_rate"] * 100),
     lambda s: s["pass_rate"] >= bench.BENCH_TARGETS["grading_pass_rate"]),
]


class BenchTab(QWidget):
    notify = Signal(str)

    def __init__(self, data_dir_getter, parent=None):
        super().__init__(parent)
        self._get_data_dir = data_dir_getter
        self.outcome = None

        self.run_button = QPushButton("运行内置基准")
        self.run_button.clicked.connect(self._on_run)
        self.summary_label = QLabel(
            "三套件一条命令跑完（examples/synthetic/grading，零 API 离线）；"
            "门限与 README 基准表同源。")
        self.summary_label.setWordWrap(True)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["套件", "指标", "当前值", "门限", "判定"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.run_button)
        layout = QVBoxLayout(self)
        layout.addLayout(buttons)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.table, 1)

    # ---- 业务（引擎 API）----

    def run_bench(self):
        """基准管线：KnowledgeError（数据目录不可用）向上抛。"""
        self.outcome = pipelines.run_bench_pipeline(self._get_data_dir())
        return self.outcome

    # ---- 槽 ----

    def _on_run(self):
        self.run_button.setEnabled(False)
        self.setCursor(Qt.WaitCursor)
        try:
            outcome = self.run_bench()
        except KnowledgeError as exc:
            self.notify.emit("基准未执行：%s" % exc)
            return
        finally:
            self.unsetCursor()
            self.run_button.setEnabled(True)
        self.show_outcome(outcome)
        self.notify.emit("基准完成：%s"
                         % ("全部达标" if outcome["all_pass"] else "有指标未达标"))

    def show_outcome(self, outcome):
        suites = outcome["suites"]
        rows = []
        for suite, metric, get_value, get_target, met in _SUITE_ROWS:
            rows.append((suite, metric, get_value(suites[suite]),
                         get_target(), met(suites[suite])))
        self.table.setRowCount(len(rows))
        for i, (suite, metric, value, target, ok) in enumerate(rows):
            for j, text in enumerate((suite, metric, value, target)):
                self.table.setItem(i, j, QTableWidgetItem(str(text)))
            verdict = QTableWidgetItem("达标" if ok else "未达标")
            verdict.setForeground(Qt.darkGreen if ok else Qt.red)
            self.table.setItem(i, 4, verdict)
        metrics = suites["synthetic"]["metrics"]
        self.summary_label.setText(
            "基准汇总：%s（examples %d 例、synthetic F1=%.4f/误报 %d、grading %d 例）"
            % ("全部达标" if outcome["all_pass"] else "有指标未达标",
               suites["examples"]["examples"], metrics["f1"],
               metrics["false_positive_count"], suites["grading"]["cases"]))
        self.outcome = outcome
