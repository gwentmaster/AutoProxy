# -*- coding: utf-8 -*-
# @Author  : gwentmaster(gwentmaster@vivaldi.net)
# I regret in my life


"""日志记录"""


import logging
from collections import deque
from typing import Deque

from PySide6.QtCore import SignalInstance


class RollingHandler(logging.Handler):
    """用于Qt的滚动日志类

    Args:
        signal: Qt信号
        max_size: 最大日志条数
    """

    def __init__(self, signal: SignalInstance, max_size: int = 50) -> None:

        super(RollingHandler, self).__init__()

        self.signal = signal
        self.queue = deque(maxlen=max_size)  # type: Deque[str]

    def emit(self, record: logging.LogRecord) -> None:

        self.queue.append(self.format(record))
        self.signal.emit("\n".join(self.queue))


def setup_log(signal: SignalInstance, level: str = "INFO"):
    """初始化日志配置

    Args:
        signal: 日志对应的Qt信号
        level: 日志记录等级
    """

    formatter = logging.Formatter(
        fmt="%(asctime)s: %(message)s",
        datefmt="%H:%M:%S"
    )
    handler = RollingHandler(signal)
    handler.setFormatter(formatter)

    logger = logging.getLogger("auto_proxy")
    logger.setLevel(level)
    logger.addHandler(handler)
