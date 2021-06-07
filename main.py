# -*- coding: utf-8 -*-
# @Author  : gwentmaster(gwentmaster@vivaldi.net)
# I regret in my life


import multiprocessing

from auto_proxy.app import App
from auto_proxy.manager import ProxyManager


if __name__ == "__main__":

    multiprocessing.freeze_support()
    App(ProxyManager()).run()
