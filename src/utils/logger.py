"""结构化日志模块"""

import logging
import sys
from datetime import datetime


def get_logger(name: str = "AI-Research") -> logging.Logger:
    """获取带结构化格式的 logger"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)-5s] %(message)s",
        datefmt="%H:%M:%S",
    ))
    logger.addHandler(handler)
    return logger


# 全局单例
log = get_logger()
