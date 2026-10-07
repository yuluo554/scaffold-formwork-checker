# -*- coding: utf-8 -*-
"""sfc 桌面 GUI 入口（M5，plan/04 §8）。

- main(argv)：QApplication + 主窗口（QTabWidget 五页签）；
- --probe：无头自检（offscreen 建窗 + 页签计数），供打包后存活探针使用
  （窗口化 exe 无控制台，验证走退出码）；
- 通知纪律：页面通知走状态栏（非模态），测试不触模态（HANDOFF-M5 口径）。
"""
import argparse
import io
import os
import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QStatusBar, QTabWidget

from .bench_tab import BenchTab
from .calc_tab import CalcTab
from .check_tab import CheckTab
from .consistency_tab import ConsistencyTab
from .grading_tab import GradingTab
from .pipelines import resolved_data_dir

TAB_ORDER = ("验算", "方案核查", "一致性", "危大分级", "基准")


class MainWindow(QMainWindow):
    """五页签主窗体：页签只消费引擎 API（gui/pipelines.py）。"""

    def __init__(self, data_dir=None):
        super().__init__()
        self._explicit_data_dir = data_dir
        self.setWindowTitle("脚手架与模板支架安全验算及危大分级工具（sfc）")

        self.tabs = QTabWidget()
        self.calc_tab = CalcTab(self.resolved_data_dir)
        self.check_tab = CheckTab(self.resolved_data_dir)
        self.consistency_tab = ConsistencyTab(self.resolved_data_dir)
        self.grading_tab = GradingTab(self.resolved_data_dir)
        self.bench_tab = BenchTab(self.resolved_data_dir)
        for title, tab in zip(TAB_ORDER, (self.calc_tab, self.check_tab,
                                          self.consistency_tab,
                                          self.grading_tab, self.bench_tab)):
            self.tabs.addTab(tab, title)
        self.setCentralWidget(self.tabs)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        for tab in (self.calc_tab, self.check_tab, self.consistency_tab,
                    self.grading_tab, self.bench_tab):
            tab.notify.connect(self._on_notify)
        self._show_data_dir()

    def resolved_data_dir(self, _=None):
        return resolved_data_dir(self._explicit_data_dir)

    def _on_notify(self, message):
        self.status.showMessage(message, 15000)

    def _show_data_dir(self):
        data_dir = self.resolved_data_dir()
        where = data_dir if data_dir else "未找到（验算/核查/分级/基准将不可用，可用 --data-dir 指定）"
        self.status.showMessage("数据目录：%s" % where)


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="sfc-gui", description="sfc 桌面 GUI（五页签：验算/方案核查/一致性/危大分级/基准）")
    parser.add_argument("--data-dir", default=None,
                        help="数据目录（含 knowledge/clauses；缺省按内嵌/自动发现）")
    parser.add_argument("--probe", action="store_true",
                        help="无头自检：offscreen 建窗并校验页签后立即退出（退出码 0=通过）")
    return parser.parse_args(argv)


def main(argv=None):
    # 窗口化 exe（console=False）无控制台：stdout/stderr 可能为 None，print 需兜底
    if sys.stdout is None:
        sys.stdout = io.StringIO()
    if sys.stderr is None:
        sys.stderr = io.StringIO()
    args = _parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.probe:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication(sys.argv[:1])
    window = MainWindow(data_dir=args.data_dir)
    if args.probe:
        titles = [window.tabs.tabText(i) for i in range(window.tabs.count())]
        if titles != list(TAB_ORDER):
            print("GUI_PROBE_FAIL tabs=%r" % (titles,))
            return 1
        data_dir = window.resolved_data_dir()
        print("GUI_PROBE_OK tabs=%d data_dir=%s" % (len(titles), data_dir))
        return 0
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
