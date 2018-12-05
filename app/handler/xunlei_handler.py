#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018-12-03 16:06
# @Author  : yves175
import atexit
import json
import os
import logging
import time
import hashlib
from urllib import quote as url_quote

from app.handler.base_handler import BaseHandler
from app.handler.exception_handler import URLError
from app.share.constants import config_files, config_files_path, LOGIN_XUN_LEI_TIME, PROTOCOL_VERSION, APP_VERSION, \
    DEVICE_MODEL, DEVICE, OS_VERSION, LOGIN_URL, HEADER_XL, VA_SID_DOWN, VA_SID_UP, USER_INFO_URL, ACCOUNT_SESSION, \
    OS_API_LEVEL, HEADER_API, FALLBACK_PORTAL, FALLBACK_UP_PORTAL, SHELL_FILE, PY3K, IPK_FILE, LOGIN_KEY_URL
from app.share.util import update_ipk

logger = logging.getLogger()


class XunLeiHandler(BaseHandler):
    def __init__(self):
        self.api_url = self.get_api_url(up=False)
        self.api_up_url = self.get_api_url(up=True)
        self.mac = self.get_mac(to_splt='').upper() + '004V'
        self.xl_uid = None
        self.xl_session = None
        self.xl_login_key = None
        self.xl_login_payload = None
        self.last_login_xun_lei = 0
        self.do_down_accelerate = False
        self.do_up_accelerate = False
        self.state = 0

    def renew_xun_lei(self):
        _ = int(LOGIN_XUN_LEI_TIME - time.time() + self.last_login_xunlei)
        if _ > 0:
            print("sleep %ds to prevent login flood" % _)
            time.sleep(_)
        self.last_login_xun_lei = time.time()
        _payload = dict(self.xl_login_payload)
        _payload.update({
            "sequenceNo": "1000001",
            "userName": str(self.xl_uid),  # wtf
            "loginKey": self.xl_loginkey,
        })
        for k in ('passWord', 'verifyKey', 'verifyCode', "sessionID"):
            del _payload[k]
        ct = self.http_req(LOGIN_KEY_URL, body=json.dumps(_payload), headers=HEADER_XL, encoding='utf-8')
        dt = json.loads(ct)

        self.load_xl(dt)
        return dt

    def load_xl(self, dt):
        if 'sessionID' in dt:
            self.xl_session = dt['sessionID']
        if 'userID' in dt:
            self.xl_uid = dt['userID']
        if 'loginKey' in dt:
            self.xl_login_key = dt['loginKey']

    def login_xun_lei(self, username, pwd):
        _ = int(time.time() - (self.last_login_xun_lei + LOGIN_XUN_LEI_TIME))
        if _ < 0:
            logger.info("sleep %ds to prevent login flood" % _)
            time.sleep(_)
        self.last_login_xun_lei = time.time()
        fake_device_id = hashlib.md5(("msfdc%s23333" % pwd).encode('utf-8')).hexdigest()

        device_sign = "div101.%s%s" % (fake_device_id, hashlib.md5(
            hashlib.sha1(("%scom.xunlei.vip.swjsq68c7f21687eed3cdb400ca11fc2263c998" % fake_device_id).encode(
                'utf-8')).hexdigest().encode('utf-8')
        ).hexdigest())
        _payload = {
            "protocolVersion": str(PROTOCOL_VERSION),
            "sequenceNo": "1000001",
            "platformVersion": "2",
            "sdkVersion": "177662",
            "peerID": self.mac,
            "businessType": "68",
            "clientVersion": APP_VERSION,
            "devicesign": device_sign,
            "isCompressed": "0",
            "userName": username,
            "passWord": pwd,
            "sessionID": "",
            "verifyKey": "",
            "verifyCode": "",
            "appName": "ANDROID-com.xunlei.vip.swjsq",
            "deviceModel": DEVICE_MODEL,
            "deviceName": DEVICE,
            "OSVersion": OS_VERSION
        }
        ct = self.http_req(LOGIN_URL, body=json.dumps(_payload), headers=HEADER_XL, encoding='utf-8')
        self.xl_login_payload = _payload
        dt = json.loads(ct)

        self.load_xl(dt)
        return dt

    def check_xun_lei_vas(self, va_sid):
        _payload = dict(self.xl_login_payload)
        _payload.update({
            "sequenceNo": "1000002",
            "vasid": str(va_sid),
            "userID": str(self.xl_uid),
            "sessionID": self.xl_session,
        })

        for k in ('userName', 'passWord', 'verifyKey', 'verifyCode'):
            del _payload[k]
        ct = self.http_req(USER_INFO_URL, body=json.dumps(_payload), headers=HEADER_XL, encoding='utf-8')
        return json.loads(ct)

    def run(self, username, pwd, save=True):
        if username[-2] == ':':
            logger.error('Error: sub account can not upgrade')
            return

        login_methods = [lambda: self.login_xun_lei(username, pwd)]
        if self.xl_session:
            login_methods.insert(0, self.renew_xun_lei)

        failed = True
        for _lm in login_methods:
            dt = _lm()
            if dt['errorCode'] != "0" or not self.xl_session or not self.xl_login_key:
                logger.error('Error: login xunlei failed, %s' % dt['errorDesc'], 'Error: login failed')
                print(dt)
            else:
                failed = False
                break
        if failed:
            return
        logger.info('Login xun lei succeeded')

        date_num = time.strftime("%Y%m%d", time.localtime(time.time()))

        vip_list = dt.get('vipList', [])

        if vip_list and vip_list[0]['isVip'] == "1" and vip_list[0]['vasType'] == "5" and \
                vip_list[0]['expireDate'] > date_num:
            self.do_down_accelerate = True
            logger.info('Expire date for chaoji member: %s' % vip_list[0]['expireDate'])

        _vas_debug = []
        for _vas, _name, _v in ((VA_SID_DOWN, 'fastdick', 'do_down_accelerate'), (VA_SID_UP, 'upstream acceleration', 'do_up_accelerate')):
            if getattr(self, _v):
                continue
            _dt = self.check_xun_lei_vas(_vas)
            if 'vipList' not in _dt or not _dt['vipList']:
                continue
            for vip in _dt['vipList']:
                if vip['vasid'] == str(_vas):
                    _vas_debug.append(vip)
                    if vip['isVip'] == "1":
                        if vip['expireDate'] < date_num:
                            logger.info('Warning: Your %s membership expires on %s' % (_name, vip['expireDate']))
                        else:
                            logger.info('Expire date for %s: %s' % (_name, vip['expireDate']))
                            setattr(self, _v, True)

        if not self.do_down_accelerate and not self.do_up_accelerate:
            logger.error(
                'Error: You are neither xunlei fastdick member nor upstream acceleration member, buy buy buy!\nDebug: %s' % _vas_debug)
            return

        if save:
            try:
                # os.remove(config_files_path)
                pass
            except:
                pass
            with open(ACCOUNT_SESSION, 'w') as f:
                f.write('%s\n%s' % (json.dumps(dt), json.dumps(self.xl_login_payload)))

        api_ret = self.api('bandwidth', no_session=True)

        _to_upgrade = []
        for _k1, _k2, _name, _v in (
                ('down', 'downstream', 'fastdick', 'do_down_accelerate'),
                ('up', 'upstream', 'upstream acceleration', 'do_up_accelerate')):
            if not getattr(self, _v):
                continue

            _ = api_ret[_k1]
            if 'can_upgrade' not in _ or not _['can_upgrade']:
                msg = 'Warning: %s can not upgrade, so sad TAT: %s' % (_name, _['message']) + 'Error: %s can not upgrade, so sad TAT' % _name
                logger.info(msg)
                setattr(self, _v, False)
            else:
                _to_upgrade.append('%s %dM -> %dM' % (
                    _k1,
                    _['bandwidth'][_k2] / 1024,
                    _['max_bandwidth'][_k2] / 1024,
                ))

        if not self.do_down_accelerate and not self.do_up_accelerate:
            logger.error("Error: neither downstream nor upstream can be upgraded")
            return

        _avail = api_ret[list(api_ret.keys())[0]]

        logger.info('To Upgrade: %s%s %s' % (_avail['province_name'], _avail['sp_name'], ", ".join(_to_upgrade)),
                    'To Upgrade: %s %s %s' % (_avail['province'], _avail['sp'], ", ".join(_to_upgrade))
                    )

        _dial_account = _avail['dial_account']

        _script_mtime = os.stat(os.path.realpath(__file__)).st_mtime
        if not os.path.exists(SHELL_FILE) or os.stat(SHELL_FILE).st_mtime < _script_mtime:
            self.make_wget_script(pwd, _dial_account)
        if not os.path.exists(IPK_FILE) or os.stat(IPK_FILE).st_mtime < _script_mtime:
            update_ipk()

        def _atexit_func():
            logger.info("Sending recover request")
            try:
                self.api('recover', extras="dial_account=%s" % _dial_account)
            except KeyboardInterrupt:
                print('Secondary ctrl+c pressed, exiting')

        atexit.register(_atexit_func)
        self.state = 0
        while True:
            has_error = False
            try:
                # self.state=1~17 keepalive,  self.state++
                # self.state=18 (3h) re-upgrade all, self.state-=18
                # self.state=100 login, self.state:=18
                if self.state == 100:
                    _dt_t = self.renew_xunlei()
                    if int(_dt_t['errorCode']):
                        time.sleep(60)
                        dt = self.login_xunlei(username, pwd)
                        if int(dt['errorCode']):
                            self.state = 100
                            continue
                    else:
                        _dt_t = dt
                    self.state = 18
                if self.state % 18 == 0:  # 3h
                    logger.info('Initializing upgrade')
                    if self.state:  # not first time
                        self.api('recover', extras="dial_account=%s" % _dial_account)
                        time.sleep(5)
                    api_ret = self.api('upgrade', extras="user_type=1&dial_account=%s" % _dial_account)
                    # print(_)
                    _upgrade_done = []
                    for _k1, _k2 in ('down', 'downstream'), ('up', 'upstream'):
                        if _k1 not in api_ret:
                            continue
                        if not api_ret[_k1]['errno']:
                            _upgrade_done.append("%s %dM" % (_k1, api_ret[_k1]['bandwidth'][_k2] / 1024))
                    if _upgrade_done:
                        logger.info("Upgrade done: %s" % ", ".join(_upgrade_done))
                else:
                    try:
                        api_ret = self.api('keepalive')
                    except Exception as ex:
                        logger.info("keepalive exception: %s" % str(ex))
                        time.sleep(60)
                        self.state = 18
                        continue
                for _k1, _k2, _name, _v in ('down', 'Downstream', 'fastdick', 'do_down_accel'), (
                        'up', 'Upstream', 'upstream acceleration', 'do_up_accel'):
                    if _k1 in api_ret and api_ret[_k1]['errno']:
                        _ = api_ret[_k1]
                        logger.info('%s error %s: %s' % (_k2, _['errno'], _['message']))
                        if _['errno'] in (513, 824):  # TEST: re-upgrade when get 513 or 824 speedup closed
                            self.state = 100
                        elif _['errno'] == 812:
                            logger.info('%s already upgraded, continuing' % _k2)
                        elif _['errno'] == 717 or _['errno'] == 718:  # re-upgrade when get 'account auth session failed'
                            self.state = 100
                        elif _['errno'] == 518:  # disable down/up when get qurey vip response user not has business property
                            logger.info("Warning: membership expired? Disabling %s" % _name)
                            setattr(self, _v, False)
                        else:
                            has_error = True
                if self.state == 100:
                    continue
            except Exception as ex:
                import traceback
                _ = traceback.format_exc()
                print(_)
                has_error = True
            if has_error:
                # sleep 5 min and repeat the same state
                time.sleep(290)  # 5 min
            else:
                self.state += 1
                time.sleep(590)  # 10 min

    def make_wget_script(self, pwd, dial_account):
        # i=1~17 keepalive, renew session, i++
        # i=18 (3h) re-upgrade, i:=0
        # i=100 login, i:=18
        xl_renew_payload = dict(self.xl_login_payload)
        xl_renew_payload.update({
            "sequenceNo": "1000001",
            "userName": str(self.xl_uid),  # wtf
            "loginKey": "$loginkey",
        })
        for k in ('passWord', 'verifyKey', 'verifyCode', "sessionID"):
            del xl_renew_payload[k]
        with open(SHELL_FILE, 'wb') as f:
            _ = '''#!/bin/ash
    TEST_URL="https://baidu.com"
    UA_XL="User-Agent: swjsq/0.0.1"

    if [ ! -z "`wget --no-check-certificate -O - $TEST_URL 2>&1|grep "100%"`" ]; then
       HTTP_REQ="wget -q --no-check-certificate -O - "
       POST_ARG="--post-data="
    else
       command -v curl >/dev/null 2>&1 && curl -kI $TEST_URL >/dev/null 2>&1 || { echo >&2 "Xunlei-FastD1ck cannot find wget or curl installed with https(ssl) enabled in this system."; exit 1; }
       HTTP_REQ="curl -ks"
       POST_ARG="--data "
    fi

    uid=''' + str(self.xl_uid) + '''
    pwd=''' + pwd + '''
    nic=eth0
    peerid=''' + self.mac + '''
    uid_orig=$uid

    last_login_xunlei=0
    login_xunlei_intv=''' + str(LOGIN_XUN_LEI_TIME) + '''

    day_of_month_orig=`date +%d`
    orig_day_of_month=`echo $day_of_month_orig|grep -oE "[1-9]{1,2}"`

    #portal=`$HTTP_REQ http://api.portal.swjsq.vip.xunlei.com:82/v2/queryportal`
    #portal_ip=`echo $portal|grep -oE '([0-9]{1,3}[\.]){3}[0-9]{1,3}'`
    #portal_port_temp=`echo $portal|grep -oE "port...[0-9]{1,5}"`
    #portal_port=`echo $portal_port_temp|grep -oE '[0-9]{1,5}'`
    portal_ip=''' + self.api_url.split(":")[0] + '''
    portal_port=''' + self.api_url.split(":")[1] + '''
    portal_up_ip=''' + self.api_up_url.split(":")[0] + '''
    portal_up_port=''' + self.api_up_url.split(":")[1] + '''

    if [ -z "$portal_ip" ]; then
        sleep 30
        portal=`$HTTP_REQ http://api.portal.swjsq.vip.xunlei.com:81/v2/queryportal`
        portal_ip=`echo $portal|grep -oE '([0-9]{1,3}[\.]){3}[0-9]{1,3}'`
        portal_port_temp=`echo $portal|grep -oE "port...[0-9]{1,5}"`
        portal_port=`echo $portal_port_temp|grep -oE '[0-9]{1,5}'`
        if [ -z "$portal_ip" ]; then
            portal_ip="''' + FALLBACK_PORTAL.split(":")[0] + '''"
            portal_port=''' + FALLBACK_PORTAL.split(":")[1] + '''
        fi
    fi

    log () {
        echo `date +%X 2>/dev/null` $@
    }

    api_url="http://$portal_ip:$portal_port/v2"
    api_up_url="http://$portal_up_ip:$portal_up_port/v2"

    do_down_accel=''' + str(int(self.do_down_accel)) + '''
    do_up_accel=''' + str(int(self.do_up_accel)) + '''

    i=100
    while true; do
        if test $i -ge 100; then
            tmstmp=`date "+%s"`
            let slp=login_xunlei_intv-tmstmp+last_login_xunlei
            if test $slp -ge 0; then
                sleep $slp
            fi
            last_login_xunlei=$tmstmp

            if [ ! -z "$loginkey" ]; then
                log "renew xunlei"
                ret=`$HTTP_REQ https://mobile-login.xunlei.com:443/loginkey $POST_ARG"''' + json.dumps(
                xl_renew_payload).replace('"', '\\"') + '''" --header "$UA_XL"`
                error_code=`echo $ret|grep -oE "errorCode...[0-9]+"|grep -oE "[0-9]+"`
                if [[ -z $error_code || $error_code -ne 0 ]]; then
                    log "renew error code $error_code"
                fi
                session_temp=`echo $ret|grep -oE "sessionID...[A-F,0-9]{32}"`
                session=`echo $session_temp|grep -oE "[A-F,0-9]{32}"`
                if [ -z "$session" ]; then
                    log "renew session is empty"
                    sleep 60
                else
                    log "session is $session"
                fi
            fi

            if [ -z "$session" ]; then
                log "login xunlei"
                ret=`$HTTP_REQ https://mobile-login.xunlei.com:443/login $POST_ARG"''' + json.dumps(
                self.xl_login_payload).replace('"', '\\"') + '''" --header "$UA_XL"`
                session_temp=`echo $ret|grep -oE "sessionID...[A-F,0-9]{32}"`
                session=`echo $session_temp|grep -oE "[A-F,0-9]{32}"`
                uid_temp=`echo $ret|grep -oE "userID...[0-9]+"`
                uid=`echo $uid_temp|grep -oE "[0-9]+"`
                if [ -z "$session" ]; then
                    log "login session is empty"
                    uid=$uid_orig
                else
                    log "session is $session"
                fi

                if [ -z "$uid" ]; then
                    #echo "uid is empty"
                    uid=$uid_orig
                else
                    log "uid is $uid"
                fi
            fi

            if [ -z "$session" ]; then
                sleep 600
                continue
            fi

            loginkey=`echo $ret|grep -oE "lk...[a-f,0-9,\.]{96}"`
            i=18
        fi

        if test $i -eq 18; then
            log "upgrade"
            _ts=`date +%s`0000
            if test $do_down_accel -eq 1; then
                $HTTP_REQ "$api_url/upgrade?peerid=$peerid&userid=$uid&sessionid=$session&user_type=1&client_type=android-swjsq-''' + APP_VERSION + '''&time_and=$_ts&client_version=androidswjsq-''' + APP_VERSION + '''&os=android-''' + OS_VERSION + '.' + OS_API_LEVEL + DEVICE_MODEL + '''&dial_account=''' + dial_account + '''"
            fi
            if test $do_up_accel -eq 1; then
                $HTTP_REQ "$api_up_url/upgrade?peerid=$peerid&userid=$uid&sessionid=$session&user_type=1&client_type=android-uplink-''' + APP_VERSION + '''&time_and=$_ts&client_version=androiduplink-''' + APP_VERSION + '''&os=android-''' + OS_VERSION + '.' + OS_API_LEVEL + DEVICE_MODEL + '''&dial_account=''' + dial_account + '''"
            fi
            i=1
            sleep 590
            continue
        fi

        sleep 1
        day_of_month_orig=`date +%d`
        day_of_month=`echo $day_of_month_orig|grep -oE "[1-9]{1,2}"`
        if [[ -z $orig_day_of_month || $day_of_month -ne $orig_day_of_month ]]; then
            log "recover"
            orig_day_of_month=$day_of_month
            _ts=`date +%s`0000
            if test $do_down_accel -eq 1; then
                $HTTP_REQ "$api_url/recover?peerid=$peerid&userid=$uid&sessionid=$session&client_type=android-swjsq-''' + APP_VERSION + '''&time_and=$_ts&client_version=androidswjsq-''' + APP_VERSION + '''&os=android-''' + OS_VERSION + '.' + OS_API_LEVEL + DEVICE_MODEL + '''&dial_account=''' + dial_account + '''"
            fi
            if test $do_up_accel -eq 1; then
                $HTTP_REQ "$api_up_url/recover?peerid=$peerid&userid=$uid&sessionid=$session&client_type=android-uplink-''' + APP_VERSION + '''&time_and=$_ts&client_version=androiduplink-''' + APP_VERSION + '''&os=android-''' + OS_VERSION + '.' + OS_API_LEVEL + DEVICE_MODEL + '''&dial_account=''' + dial_account + '''"
            fi
            sleep 5
            i=100
            continue
        fi


        log "keepalive"
        _ts=`date +%s`0000
        if test $do_down_accel -eq 1; then
            ret=`$HTTP_REQ "$api_url/keepalive?peerid=$peerid&userid=$uid&sessionid=$session&client_type=android-swjsq-''' + APP_VERSION + '''&time_and=$_ts&client_version=androidswjsq-''' + APP_VERSION + '''&os=android-''' + OS_VERSION + '.' + OS_API_LEVEL + DEVICE_MODEL + '''&dial_account=''' + dial_account + '''"`
            if [[ -z $ret ]]; then
                sleep 60
                i=18
                continue
            fi
            if [ ! -z "`echo $ret|grep "not exist channel"`" ]; then
                i=100
            fi
            if  [ ! -z "`echo $ret|grep "user not has business property"`" ]; then
                log "membership expired? disabling fastdick"
                do_down_accel=0
            fi
        fi
        if test $do_up_accel -eq 1; then
            ret=`$HTTP_REQ "$api_up_url/keepalive?peerid=$peerid&userid=$uid&sessionid=$session&client_type=android-uplink-''' + APP_VERSION + '''&time_and=$_ts&client_version=androiduplink-''' + APP_VERSION + '''&os=android-''' + OS_VERSION + '.' + OS_API_LEVEL + DEVICE_MODEL + '''&dial_account=''' + dial_account + '''"`
            if [[ -z $ret ]]; then
                sleep 60
                i=18
                continue
            fi
            if [ ! -z "`echo $ret|grep "not exist channel"`" ]; then
                i=100
            fi
            if  [ ! -z "`echo $ret|grep "user not has business property"`" ]; then
                log "membership expired? disabling upstream acceleration"
                do_up_accel=0
            fi
        fi

        if test $i -ne 100; then
            let i=i+1
            sleep 590
        fi
    done
    '''.replace("\r", "")
            if PY3K:
                _ = _.encode("utf-8")
            f.write(_)

    def api(self, cmd, extras='', no_session=False):
        ret = {}
        for _k1, api_url_k, _clienttype, _v in (
                ('down', 'api_url', 'swjsq', 'do_down_accelerate'), ('up', 'api_up_url', 'uplink', 'do_up_accelerate')):
            if not getattr(self, _v):
                continue
            while True:
                api_url = getattr(self, api_url_k)
                url = 'http://%s/v2/%s?%sclient_type=android-%s-%s&peerid=%s&time_and=%d&client_version=android%s-%s&userid=%s&os=android-%s%s' % (
                    api_url,
                    cmd,
                    ('sessionid=%s&' % self.xl_session) if not no_session else '',
                    _clienttype, APP_VERSION,
                    self.mac,
                    time.time() * 1000,
                    _clienttype, APP_VERSION,
                    self.xl_uid,
                    url_quote("%s.%s%s" % (OS_VERSION, OS_API_LEVEL, DEVICE_MODEL)),
                    ('&%s' % extras) if extras else '',
                )
                try:
                    ret[_k1] = {}
                    ret[_k1] = json.loads(self.http_req(url, headers=HEADER_API))
                    break
                except URLError as ex:
                    logger.info("Warning: error during %sapi connection: %s, use portal: %s" % (_k1, str(ex), api_url))
                    if (_k1 == 'down' and api_url == FALLBACK_PORTAL) or (
                            _k1 == 'up' and api_url == FALLBACK_UP_PORTAL):
                        logger.error("Error: can't connect to %s api" % _k1)
                        return
                    if _k1 == 'down':
                        setattr(self, api_url_k, FALLBACK_PORTAL)
                    elif _k1 == 'up':
                        setattr(self, api_url_k, FALLBACK_UP_PORTAL)
        return ret

    def server_run(self):
        if os.path.exists(config_files_path):
            username = str(config_files.get("username", ""))
            pwd = str(config_files.get("password", ""))
            self.run(username, pwd)


xun_lei_handler = XunLeiHandler()
