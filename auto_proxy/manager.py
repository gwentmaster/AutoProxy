# -*- coding: utf-8 -*-
# @Author  : gwentmaster(gwentmaster@vivaldi.net)
# I regret in my life


"""代理管理"""


import ctypes
import logging
import random
import time
import winreg
from dataclasses import dataclass
from math import inf as INF
from queue import Empty, Queue
from threading import Event
from typing import Any, Dict, Optional, Union

import httpx


@dataclass
class ProxyItem(object):
    """代理队列中的代理项

    Attributes:
        priority: 优先级, 数值低的优先出队
        proxy: `httpx.Proxy` 代理类
    """

    priority: int
    proxy: httpx.Proxy


class ProxyQueue(Queue):
    """
    自定义代理队列

    重写了入队方法, 保证队列总是按优先级排序且无重复代理
    """

    def _put(self, item: ProxyItem) -> None:
        """入队方法

        Args:
            item: 待入队代理项
        """

        if item in self.queue:
            self.queue.remove(item)

        i = 0
        for i, queue_item in enumerate(self.queue):
            if item.priority <= queue_item.priority:
                break
        else:
            i += 1

        self.queue.insert(i, item)

    def get_random(
        self,
        block: bool = True,
        timeout: Optional[float] = None
    ) -> ProxyItem:
        """从队列中随机获取一代理项, 用于校验代理是否有效, 改编自 `Queue.get`

        Args:
            block: 是否阻塞, 默认True
            timeout: 超时时间

        Returns:
            随机的代理项
        """

        with self.not_empty:
            if not block:
                if not self._qsize():
                    raise Empty
            elif timeout is None:
                while not self._qsize():
                    self.not_empty.wait()
            elif timeout < 0:
                raise ValueError("'timeout' must be a non-negative number")
            else:
                endtime = time.monotonic() + timeout
                while not self._qsize():
                    remaining = endtime - time.monotonic()
                    if remaining <= 0.0:
                        raise Empty
                    self.not_empty.wait(remaining)
            item = random.choice(self.queue)
            self.queue.remove(item)
            self.not_full.notify()
            return item


class ProxyManager(object):
    """代理管理类"""

    def __init__(self) -> None:

        self.reg = winreg.CreateKey(
            winreg.HKEY_CURRENT_USER,
            R"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        )
        self.client = httpx.Client(trust_env=False)
        self.logger = logging.getLogger("auto_proxy.manager")
        self.proxy_queue = ProxyQueue()  # type: Queue[ProxyItem]
        self.must_quit = Event()

    def __del__(self) -> None:

        self.client.close()

    def fetch_proxy(self) -> None:
        """获取代理"""

        url = "https://ip.jiangxianli.com/api/proxy_ips"

        params = {
            "country": "中国",
            "order_by": "validated_at",
            "order_rule": "ASC"
        }  # type: Dict[str, Union[str, int]]

        max_page = INF
        page = 1

        try:
            while page < max_page:

                params["page"] = page
                resp_data = self.client.get(
                    url=url,
                    params=params
                ).json()

                for dic in resp_data["data"]["data"]:
                    self.proxy_queue.put(ProxyItem(
                        priority=50,
                        proxy=httpx.Proxy(url=(
                            f"{dic['protocol']}://"
                            + f"{dic['ip']}:{dic['port']}"
                        ))
                    ))

                self.logger.info(f"第{page}页代理获取完成")

                max_page = resp_data["data"]["last_page"]
                page += 1

            self.logger.info("代理获取完成")

        except Exception as e:
            self.logger.error("代理获取失败")
            if isinstance(e, httpx.TimeoutException):
                self.logger.error("免费代理服务不稳定, 若持续获取失败, 考虑换个时间段再尝试")
            self.logger.debug(f"error_type: {type(e)}; error_msg: {e}")

    async def averify_proxy(self):
        """校验代理有效性"""

        async with httpx.AsyncClient(trust_env=False) as client:

            while not self.must_quit.wait(0.25):

                try:
                    item = self.proxy_queue.get_random(timeout=2)
                except Empty:
                    continue

                try:
                    self.proxy_hack(client, item.proxy)
                    await client.get("http://www.baidu.com")
                    item.priority = 0
                    self.proxy_queue.put(item)
                except Exception:
                    item.priority += 10
                    if item.priority < 100:
                        self.proxy_queue.put(item)

    def proxy_hack(
        self,
        client: httpx.AsyncClient,
        proxy: httpx.Proxy
    ) -> None:
        """因 `httpx.AsyncClinet` 没有更改代理设置的方法, 通过此方法进行修改

        Args:
            client: 需修改代理的会话类
            proxy: 需设置的代理
        """

        proxy_map = client._get_proxy_map(proxy, False)
        proxies = {
            httpx._utils.URLPattern(key): (
                None if proxy is None
                else client._init_proxy_transport(
                    proxy,
                    verify=True,
                    cert=None,
                    http2=False,
                    limits=httpx._config.DEFAULT_LIMITS,
                    trust_env=False
                )
            )
            for key, proxy in proxy_map.items()
        }
        client._proxies = dict(sorted(proxies.items()))

    def set_reg_key(self, key: str, value: Any) -> None:
        """设置注册表的值

        Args:
            key: 注册表键名
            value: 需设置的值
        """

        _, reg_type = winreg.QueryValueEx(self.reg, key)
        winreg.SetValueEx(self.reg, key, 0, reg_type, value)

    def refresh_reg_setting(self) -> None:
        """刷新代理设置, 通过注册表设置代理后需刷新设置后生效"""

        INTERNET_OPTION_REFRESH = 37
        INTERNET_OPTION_SETTINGS_CHANGED = 39

        ctypes.windll.Wininet.InternetSetOptionW(
            0, INTERNET_OPTION_REFRESH,
            0, 0
        )
        ctypes.windll.Wininet.InternetSetOptionW(
            0, INTERNET_OPTION_SETTINGS_CHANGED,
            0, 0
        )

    def set_proxy(self) -> Optional[str]:
        """设置系统代理

        Returns:
            设置成功返回代理url, 未设置返回None
        """

        try:
            proxy = self.proxy_queue.get_nowait().proxy
        except Empty:
            self.logger.info("代理为空, 请先获取代理")
            return None

        self.set_reg_key("ProxyEnable", 1)
        self.set_reg_key("ProxyOverride", "*.local;<local>")
        self.set_reg_key("ProxyServer", f"{proxy.url.host}:{proxy.url.port}")

        self.refresh_reg_setting()

        self.logger.info(f"代理已设置为: {proxy.url}")
        return str(proxy.url)

    def stop_proxy(self) -> None:
        """停止系统代理"""

        self.set_reg_key("ProxyEnable", 0)
        self.refresh_reg_setting()

        self.logger.info("已停止代理")
