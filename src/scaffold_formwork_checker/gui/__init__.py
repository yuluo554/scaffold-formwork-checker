# -*- coding: utf-8 -*-
"""M5 桌面 GUI（PySide6，plan/04 §8）：五页签只消费引擎 API。

分层纪律（HANDOFF-M5 口径 17）：
- pipelines.py：GUI 侧唯一编排层（零 Qt），与 CLI 同款引擎函数调用；
- specs.py：验算页动态表单的字段规格与默认卡（纯数据，零 Qt）；
- *_tab.py / app.py：Qt 表现层——只做表单采集、结果展示、导出对话框，
  不含任何判定逻辑（数值结论永远来自引擎）。

GUI 测试纪律：offscreen 平台须在首次导入 PySide6 前设置（tests/test_gui.py
模块头部）；页面通知走可注入 notify 信号（不弹模态框）；文件对话框只允许
出现在按钮槽内。
"""
