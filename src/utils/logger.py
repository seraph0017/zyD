#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
from logging.handlers import RotatingFileHandler
from src.config.config import get_config

def setup_logger(name: str) -> logging.Logger:
    """设置日志记录器"""
    config = get_config()
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.log.level))
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 文件处理器
    log_dir = "data/logs"
    os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    
    # 格式化器
    formatter = logging.Formatter(config.log.format)
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger