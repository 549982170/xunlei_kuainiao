#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018-12-03 15:53
# @Author  : yves175
import os
import json
import sys
from logging import config

# 配置文件
config_files_path = os.path.join('config', "config.json")
config_files = json.load(open(config_files_path, 'r'))

# 默认配置日志路径
log_file_path = os.path.join('config', 'logger.conf')

# 获取IP端口API
API = "http://api%s.%sportal.swjsq.vip.xunlei.com:%d/v2/queryportal"

# 认证失败时直接返回下载IP
FALLBACK_PORTAL = "180.97.85.185:12700"
# 认证失败时直接返回上传IP
FALLBACK_UP_PORTAL = "153.37.208.185:81"

LOGIN_XUN_LEI_TIME = 600  # 登录时间间隔(秒)

APP_VERSION = "2.4.1.3"
PROTOCOL_VERSION = 200
VA_SID_DOWN = 14
VA_SID_UP = 33

USER_INFO_URL = 'https://mobile-login.xunlei.com:443/getuserinfo'

UNICODE_WARNING_SHOWN = False

PY3K = sys.version_info[0] == 3

ACCOUNT_SESSION = os.path.join('session', '.xunlei.session')
SHELL_FILE = os.path.join('shell', 'xunlei_wget.sh')
IPK_FILE = os.path.join('ipk', 'xunlei_0.0.1_all.ipk')

LOGIN_XUNLEI_INTV = 600  # do not login twice in 10min

DEVICE = "SmallRice R1"
DEVICE_MODEL = "R1"
OS_VERSION = "5.0.1"
OS_API_LEVEL = "24"
OS_BUILD = "LRX22C"

PY3K = sys.version_info[0] == 3

# 迅雷登录url
LOGIN_URL = 'https://mobile-login.xunlei.com:443/login'

LOGIN_KEY_URL = 'https://mobile-login.xunlei.com:443/loginkey '

HEADER_XL = {
    'Content-Type': '',
    'Connection': 'Keep-Alive',
    'Accept-Encoding': 'gzip',
    'User-Agent': 'android-async-http/xl-acc-sdk/version-2.1.1.177662'
}
HEADER_API = {
    'Content-Type': '',
    'Connection': 'Keep-Alive',
    'Accept-Encoding': 'gzip',
    'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android %s; %s Build/%s)' % (OS_VERSION, DEVICE_MODEL, OS_BUILD)
}

# 配置日志
config.fileConfig(log_file_path)
