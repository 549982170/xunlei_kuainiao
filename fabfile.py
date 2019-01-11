# coding:utf-8
# !/user/bin/python
import os
import json
from fabric import task
from fabric import Connection

# 配置文件
config_files_path = os.path.join('config', "config.json")
config_files = json.load(open(config_files_path, 'r'))


def update_config(connect):
    run_host = connect.host if connect.host.split(".").__len__() == 4 else config_files["route_host"]  # 默认测试服
    conf = {
        "host": run_host,
        "user": config_files["route_username"],
        "port": config_files["route_port"],
        "connect_kwargs": {"password": config_files["route_password"]},
    }
    for k, v in conf.items():
        if hasattr(connect, k):
            setattr(connect, k, v)
    return connect


@task
def run_route_xun_lei(connect_obj):
    """运行服务器上的迅雷"""
    with update_config(connect_obj) as c:
        with c.cd("/tmp/mnt/yizhiwu/data/appsystems/xunlei_kuainiao"):
            c.run('python ./swjsq.py &', warn=True, pty=False)


if __name__ == '__main__':
    server = Connection(host=config_files["route_host"])
    run_route_xun_lei(server)
