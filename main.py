#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证码处理系统主入口
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 导入并运行主程序
if __name__ == "__main__":
    from src.main import main
    main()