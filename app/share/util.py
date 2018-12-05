#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018-12-03 15:56
# @Author  : yves175
import json
import os
import re
import sys
import tarfile
import urllib2
import zlib
import random
import urllib2
from urllib2 import URLError
from urllib import quote as url_quote
from cStringIO import StringIO as sio

from app.share.constants import PY3K, IPK_FILE


def rand_mac():
    rand_mac_data = ""
    for i in range(1, 7):
        rand_str = "".join(random.sample("0123456789ABCDEF", 2))
        rand_mac_data += rand_str
    return rand_mac_data


def update_ipk():
    def _sio(s=None):
        if not s:
            return sio()
        if PY3K:
            return sio(bytes(s, "ascii"))
        else:
            return sio(s)

    def flen(fobj):
        pos = fobj.tell()
        fobj.seek(0)
        _ = len(fobj.read())
        fobj.seek(pos)
        return _

    def add_to_tar(tar, name, sio_obj, perm=420):
        info = tarfile.TarInfo(name=name)
        info.size = flen(sio_obj)
        info.mode = perm
        sio_obj.seek(0)
        tar.addfile(info, sio_obj)

    if os.path.exists(IPK_FILE):
        os.remove(IPK_FILE)
    ipk_fobj = tarfile.open(name=IPK_FILE, mode='w:gz')

    data_stream = sio()
    data_fobj = tarfile.open(fileobj=data_stream, mode='w:gz')
    # /usr/bin/swjsq
    data_content = open(IPK_FILE, 'rb')
    add_to_tar(data_fobj, './bin/swjsq', data_content, perm=511)
    # /etc/init.d/swjsq
    data_content = _sio('''#!/bin/sh /etc/rc.common
START=90
STOP=15
USE_PROCD=1

start_service()
{
	procd_open_instance
	procd_set_param respawn ${respawn_threshold:-3600} ${respawn_timeout:-5} ${respawn_retry:-5}
	procd_set_param command /bin/swjsq
	procd_set_param stdout 1
	procd_set_param stderr 1
	procd_close_instance
}
''')
    add_to_tar(data_fobj, './etc/init.d/swjsq', data_content, perm=511)
    # wrap up
    data_fobj.close()
    add_to_tar(ipk_fobj, './data.tar.gz', data_stream)
    data_stream.close()

    control_stream = sio()
    control_fobj = tarfile.open(fileobj=control_stream, mode='w:gz')
    control_content = _sio('''Package: swjsq
Version: 0.0.1
Depends: libc
Source: none
Section: net
Maintainer: fffonion
Architecture: all
Installed-Size: %d
Description:  Xunlei Fast Dick
''' % flen(data_content))
    add_to_tar(control_fobj, './control', control_content)
    control_fobj.close()
    add_to_tar(ipk_fobj, './control.tar.gz', control_stream)
    control_stream.close()

    data_content.close()
    control_content.close()

    debian_binary_stream = _sio('2.0\n')
    add_to_tar(ipk_fobj, './debian-binary', debian_binary_stream)
    debian_binary_stream.close()

    ipk_fobj.close()
