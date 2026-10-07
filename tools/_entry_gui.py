# -*- coding: utf-8 -*-
"""sfc-gui.exe（桌面 GUI）冻结入口：与开发态 sfc-gui 同一 main。"""
import sys

from scaffold_formwork_checker.gui.app import main

if __name__ == "__main__":
    sys.exit(main())
