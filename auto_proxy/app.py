# -*- coding: utf-8 -*-
# @Author  : gwentmaster(gwentmaster@vivaldi.net)
# I regret in my life


"""应用主逻辑"""


import asyncio
import logging
import sys
from threading import Event
from typing import cast, List

from PySide6.QtCore import QObject, Qt, QThread, Signal, SignalInstance
from PySide6.QtGui import QStandardItem, QStandardItemModel, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QListView,
    QMainWindow,
    QVBoxLayout,
    QWidget
)

from auto_proxy.gui import UiMainWindow
from auto_proxy.log import setup_log
from auto_proxy.manager import ProxyItem, ProxyManager


class VerifyProxyThread(QThread):
    """校验代理有效性的线程

    Args:
        manager: 代理管理类
    """

    def __init__(self, manager: ProxyManager, *args, **kwargs) -> None:

        super(VerifyProxyThread, self).__init__(*args, **kwargs)
        self.manager = manager

    def run(self) -> None:

        self.manager.fetch_proxy()
        asyncio.run(self.manager.averify_proxy())


class FetchProxyThread(QThread):
    """获取代理的线程

    Attributes:
        signal_proxy_fetched: 代理获取成功时发出

    Args:
        manager: 代理管理类
    """

    signal_proxy_fetched = cast(SignalInstance, Signal(name="proxy_fetched"))

    def __init__(self, manager: ProxyManager, *args, **kwargs) -> None:

        super(FetchProxyThread, self).__init__(*args, **kwargs)
        self.manager = manager

    def run(self) -> None:

        self.manager.fetch_proxy()
        self.signal_proxy_fetched.emit()


class RefreshProxyThread(QThread):
    """刷新已获取代理列表的线程

    Attributes:
        signal_proxy_list: 将所有已获取到的代理项的列表每秒发送一次的信号
        must_quit: `Threading.Event` 类, 通过调用其 `set` 方法来退出线程

    Args:
        manager: 代理管理类
    """

    signal_proxy_list = cast(SignalInstance, Signal(list, name="proxy_list"))

    def __init__(self, manager: ProxyManager, *args, **kwargs) -> None:

        super(RefreshProxyThread, self).__init__(*args, **kwargs)
        self.manager = manager
        self.must_quit = Event()

    def run(self) -> None:

        self.must_quit.clear()
        while not self.must_quit.wait(1):

            self.signal_proxy_list.emit(
                [p for p in self.manager.proxy_queue.queue]
            )


class ProxyCheckWidget(QWidget):
    """查看已获取代理的窗口

    Args:
        refresh_thread: 刷新已获取代理列表的线程
    """

    def __init__(
        self,
        refresh_thread: RefreshProxyThread,
        *args,
        **kwargs
    ) -> None:

        super(ProxyCheckWidget, self).__init__(*args, **kwargs)

        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setWindowTitle("代理查看")

        self.list_proxy_pool = QListView()
        self.list_proxy_pool.setMinimumHeight(500)
        self.model_proxy_pool = QStandardItemModel()
        self.list_proxy_pool.setModel(self.model_proxy_pool)

        self._layout = QVBoxLayout(self)
        self._layout.addWidget(self.list_proxy_pool)

        self._thread = refresh_thread
        self._thread.signal_proxy_list.connect(self.refresh)

    def refresh(self, proxy_items: List[ProxyItem]):
        """刷新已获取的代理"""

        self.model_proxy_pool.removeRows(0, self.model_proxy_pool.rowCount())

        for p in proxy_items:

            widget = QLabel(str(p.proxy.url))
            if p.priority <= 30:
                color = "green"
            elif p.priority >= 60:
                color = "red"
            else:
                color = "yellow"
            widget.setStyleSheet(f"QLabel {{background-color: {color}}}")

            item = QStandardItem()
            item.setSelectable(False)
            self.model_proxy_pool.appendRow(item)

            self.list_proxy_pool.setIndexWidget(item.index(), widget)

    def show(self) -> None:
        """窗口打开时开启刷新代理的线程"""

        self._thread.start()
        super(ProxyCheckWidget, self).show()

    def closeEvent(self, event) -> None:
        """窗口关闭时退出刷新代理的线程"""

        self._thread.must_quit.set()
        self._thread.terminate()


class App(QObject):

    signal_log_emit = cast(SignalInstance, Signal(str, name="log_emit"))

    def __init__(self, manager: ProxyManager) -> None:

        self.proxy_manager = manager

        super(App, self).__init__()
        self.app = QApplication(sys.argv)
        self.main_window = QMainWindow()

        self.ui = UiMainWindow(self.main_window)

        self.logger = logging.getLogger("auto_proxy.app")
        setup_log(self.signal_log_emit, "DEBUG")

        self.init_thread()
        self.init_signal()

    def init_thread(self) -> None:
        """初始化子线程"""

        self.thread_proxy_verify = VerifyProxyThread(self.proxy_manager)
        self.thread_proxy_fetch = FetchProxyThread(self.proxy_manager)
        self.thread_proxy_refresh = RefreshProxyThread(self.proxy_manager)

    def init_signal(self) -> None:
        """信号与槽函数绑定"""

        self.ui.button_proxy_fetch.clicked.connect(self.handle_proxy_fetch)
        self.ui.button_proxy_set.clicked.connect(self.handle_proxy_set)
        self.ui.button_proxy_check.clicked.connect(self.handle_proxy_check)
        self.ui.button_proxy_stop.clicked.connect(self.handle_proxy_stop)

        self.signal_log_emit.connect(self.handle_log_emit)

        self.thread_proxy_fetch.signal_proxy_fetched.connect(
            self.handle_proxy_fetched
        )

    def handle_log_emit(self, text: str) -> None:
        """日志记录

        Args:
            text: 需在日志区展示的日志
        """

        cursor = self.ui.text_log.textCursor()  # type: QTextCursor
        self.ui.text_log.setText(text)
        self.ui.text_log.moveCursor(cursor.End)

    def handle_proxy_set(self) -> None:
        """设置系统代理"""

        cproxy = self.proxy_manager.set_proxy()
        if cproxy:
            self.ui.text_cproxy.setText(cproxy)

    def handle_proxy_fetch(self) -> None:
        """获取代理"""

        if self.thread_proxy_fetch.isRunning():
            self.ui.button_proxy_fetch.setEnabled(False)
            self.logger.error("获取代理中...")
            return None

        self.thread_proxy_fetch.start()
        self.ui.button_proxy_fetch.setEnabled(False)
        self.logger.info("获取代理中...")

    def handle_proxy_fetched(self) -> None:
        """代理获取成功"""

        self.ui.button_proxy_fetch.setEnabled(True)

    def handle_proxy_check(self) -> None:
        """查看代理"""

        self.window_proxy_check = ProxyCheckWidget(self.thread_proxy_refresh)
        self.window_proxy_check.show()

    def handle_proxy_stop(self) -> None:
        """停止系统代理"""

        self.proxy_manager.stop_proxy()
        self.ui.text_cproxy.setText("")

    def exec_(self) -> int:
        """应用退出时关退出所有子线程并关闭系统代理"""

        code = self.app.exec_()

        self.thread_proxy_verify.terminate()
        self.thread_proxy_fetch.terminate()
        self.thread_proxy_refresh.terminate()

        self.proxy_manager.stop_proxy()

        return code

    def run(self) -> None:
        """应用启动, 并开启代理校验的线程"""

        self.main_window.show()

        self.thread_proxy_verify.start()

        sys.exit(self.exec_())
