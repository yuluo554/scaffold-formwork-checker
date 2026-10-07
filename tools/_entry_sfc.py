# -*- coding: utf-8 -*-
"""sfc.exe（CLI 控制台）冻结入口：与开发态 sfc 同一 main（单一事实源）。"""
import sys

from scaffold_formwork_checker.cli import main

if __name__ == "__main__":
    sys.exit(main())
