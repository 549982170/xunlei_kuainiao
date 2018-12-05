#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018-12-03 16:02
# @Author  : yves175
import json
import os
import re
import sys
import urllib2
import zlib
import logging

from app.share.constants import FALLBACK_UP_PORTAL, FALLBACK_PORTAL, API
from app.share.util import rand_mac

logger = logging.getLogger()


class BaseHandler(object):
    def __init__(self):
        pass

    def get_api_url(self, up=False):
        portal = None
        if up:
            interface_ip = FALLBACK_UP_PORTAL
            portals = (("", "up", 80),)
        else:
            interface_ip = FALLBACK_PORTAL
            portals = (("", "", 81), ("2", "", 81), ("", "", 82))
        for ca in portals:
            try:
                portal = json.loads(self.http_req(API % ca))
                interface_ip = '%s:%s' % (portal['interface_ip'], portal['interface_port'])
            except:
                pass
            else:
                break

        if not portal or portal.get('errno'):
            logger.error('Warning: get interface_ip failed, use fallback address')
        return interface_ip

    def http_req(self, url, headers={}, body=None, encoding='utf-8'):
        req = urllib2.Request(url)
        for k in headers:
            req.add_header(k, headers[k])
        if sys.version.startswith('3') and isinstance(body, str):
            body = bytes(body, encoding='ascii')
        resp = urllib2.urlopen(req, data=body, timeout=60)
        buf = resp.read()
        if buf.startswith(b'\037\213'):
            try:
                buf = zlib.decompress(buf, 16 + zlib.MAX_WBITS)
            except Exception as ex:
                print('Warning: malformed gzip response (%s).' % str(ex))
        ret = buf.decode(encoding)
        if sys.version.startswith('3') and isinstance(ret, bytes):
            ret = str(ret)
        return ret

    def get_mac(self, nic='', to_splt=':'):
        fallback_mac = rand_mac()
        if os.name == 'nt':
            cmd = 'ipconfig /all'
            splt = '-'
        elif os.name == "posix":
            if os.path.exists('/usr/bin/ip') or os.path.exists('/bin/ip'):
                if nic:
                    cmd = 'ip link show dev %s' % nic
                else:
                    cmd = 'ip link show up | grep -v loopback'
            else:
                cmd = 'ifconfig %s' % (nic or '-a')
            splt = ':'
        else:
            return fallback_mac
        try:
            r = os.popen(cmd).read()
            if r:
                _ = re.findall('((?:[0-9A-Fa-f]{2}%s){5}[0-9A-Fa-f]{2})' % splt, r)
                if _:
                    fallback_mac = _[0].replace(splt, to_splt)
        except:
            pass
        finally:
            return fallback_mac
