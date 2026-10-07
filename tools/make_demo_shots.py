# -*- coding: utf-8 -*-
"""M5 演示截图（plan/05 M5 演示物）：五页签真实运行态 → docs/images/*.png。

实录坑（skill M5 三条）：offscreen 平台拿不到系统字体（中文渲染成方块）——
截图必须走 native QPA；widget.grab() 无需 show 上屏（不闪窗）；6.6 的
QPixmap.save(BytesIO) 不可用 → 走 QBuffer。

用法（仓库根）：python tools/make_demo_shots.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PySide6.QtCore import QBuffer, QIODevice  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from scaffold_formwork_checker.gui.app import MainWindow  # noqa: E402

REPO_DATA = os.path.join(ROOT, "data", "synthetic")
OUT_DIR = os.path.join(ROOT, "docs", "images")


def _save_pixmap(pixmap, path):
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    ok = pixmap.save(buf, "PNG")
    if not ok:
        raise RuntimeError("pixmap save 失败：%s" % path)
    with open(path, "wb") as f:
        f.write(bytes(buf.data()))
    print("截图：%s (%d bytes)" % (os.path.relpath(path, ROOT), os.path.getsize(path)))


def _populate(window):
    """五页签真实运行态（每个按钮流程真实跑引擎，不摆假数据）。

    路径一律相对仓库根：截图入公开仓后不泄露本机绝对路径（M6 脱敏口径）。
    """
    calc = window.calc_tab
    calc._on_run()

    check = window.check_tab
    check.set_scheme_path(os.path.join("data", "synthetic", "SY-two-sheets-01.docx"))
    check._on_run()

    cons = window.consistency_tab
    cons.set_paths(os.path.join("data", "synthetic", "SY-two-sheets-01.docx"))
    cons._on_run()

    grading = window.grading_tab
    grading.set_scheme_path(os.path.join("data", "synthetic", "SY-grading-missing-01.docx"))
    grading._on_run()

    bench = window.bench_tab
    bench._on_run()


def main():
    assert os.path.basename(os.getcwd()) == os.path.basename(ROOT) or \
        os.path.isfile(os.path.join(os.getcwd(), "pyproject.toml")), \
        "请在仓库根运行（相对路径截图口径）"
    app = QApplication.instance() or QApplication(sys.argv[:1])
    window = MainWindow()
    window.resize(1280, 860)
    _populate(window)
    os.makedirs(OUT_DIR, exist_ok=True)
    names = ("01-calc", "02-check", "03-consistency", "04-grading", "05-bench")
    for i in range(window.tabs.count()):
        window.tabs.setCurrentIndex(i)
        app.processEvents()
        _save_pixmap(window.tabs.currentWidget().grab(),
                     os.path.join(OUT_DIR, "gui-tab-%s.png" % names[i]))
    print("GUI_SHOTS_OK")


if __name__ == "__main__":
    main()
