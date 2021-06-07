# -*- coding: utf-8 -*-
# @Author  : gwentmaster(gwentmaster@vivaldi.net)
# I regret in my life


"""gui界面"""


from typing import Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QFont
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget
)


class UiMainWindow(object):

    def __init__(self, main_window: QMainWindow) -> None:

        self.main_window = main_window

        self.setup_ui()

    def setup_ui(self) -> None:

        self.main_window.setWindowTitle("AotuProxy - Powered by Python")

        self.widget = QWidget(self.main_window)
        self.main_window.resize(400, 500)
        self.main_window.setCentralWidget(self.widget)

        """====================  当前代理区   ===================="""

        self.label_cproxy = QLabel("当前代理: ")
        self.text_cproxy = QTextBrowser()
        self.text_cproxy.setFont(QFont("Microsoft YaHei", 20))

        self.layout_cproxy = QVBoxLayout()
        self.layout_cproxy.addWidget(self.label_cproxy)
        self.layout_cproxy.addWidget(self.text_cproxy)

        """====================  功能按钮区   ===================="""

        self.button_proxy_fetch = self.new_button("获取代理", (80, 50), flat=False)
        self.button_proxy_set = self.new_button("切换代理", (80, 50), flat=False)
        self.button_proxy_check = self.new_button("查看代理", (80, 50), flat=False)
        self.button_proxy_stop = self.new_button("停止代理", (80, 50), flat=False)

        self.layout_common_command = QGridLayout()
        self.layout_common_command.addWidget(self.button_proxy_fetch, 0, 0)
        self.layout_common_command.addWidget(self.button_proxy_set, 0, 1)
        self.layout_common_command.addWidget(self.button_proxy_check, 1, 0)
        self.layout_common_command.addWidget(self.button_proxy_stop, 1, 1)

        """====================   日志区    ===================="""

        self.text_log = QTextBrowser()
        self.text_log.setFont(QFont("Microsoft YaHei", 10))

        """====================  主窗口布局   ===================="""

        self.layout_main = QVBoxLayout(self.widget)
        self.layout_main.addLayout(self.layout_cproxy)
        self.layout_main.addLayout(self.layout_common_command)
        self.layout_main.addWidget(self.text_log)
        self.widget.setLayout(self.layout_main)

    def new_button(
        self,
        text: str,
        size: Tuple[int, int] = None,
        flat: bool = True,
        click_effect: bool = True
    ) -> QPushButton:

        button = QPushButton(self.widget, text=text)

        if size is not None:
            button.setFixedSize(*size)

        if click_effect is True:
            button.setStyleSheet(
                ":pressed {padding-left: 2px; padding-top: 2px}"
            )

        button.setFlat(flat)
        button.setCursor(QCursor(Qt.PointingHandCursor))

        return button
