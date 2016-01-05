import zc.zk
from kazoo.client import KazooClient
import time
import json
import os
import sys
import psutil
import base64 
import logging #https://kazoo.readthedocs.org/en/latest/basic_usage.html
logging.basicConfig()

"""
0) load zookeeper from file written by chef
1) get ip address from file
2) register server
3) If change in servers then rerun chef
"""

# with open('ha_services.json') as data_file:    
#     service_hash = json.load(data_file)
#zk_host_list = '107.170.219.233'


SETTINGS_FILE='/etc/ec2/meta_data.yaml'
from yaml import load, dump
from yaml import Loader, Dumper
f = open(SETTINGS_FILE)
parms = load(f, Loader=Loader)
f.close()

environment = parms['environment']
location = parms['location']
datacenter = parms['datacenter']
slug = parms['slug']

zk_host_list = open('/var/zookeeper_hosts.json').readlines()[0]

zk_host_list = zk_host_list.split(',')
for i in xrange(len(zk_host_list)):
    zk_host_list[i]=zk_host_list[i]+':2181' 
zk_host_str = ','.join(zk_host_list)

def get_zk_conn():
    zk = KazooClient(hosts=zk_host_str, read_only=True)
    zk.start()
    return zk
zk = get_zk_conn()

def create_cgf(path,addresses):
    
    server_type = path.split('-')[1]
    if service_hash[server_type].find(':80')>=0:
        mode = 'http'
    else:
        mode = 'tcp'
    print server_type
    temp = []
    for index,ip in enumerate(list(addresses)):
        temp.append('server %s-%s %s:%s check' % (server_type,index+1,ip,service_hash[server_type].split(':')[1]))
    temp = '\n'.join(temp)
    temp_ha = """
    listen %s  %s
    mode %s
    option tcpka
    option tcplog
    balance roundrobin
    %s
    """ % (server_type,service_hash[server_type],mode,temp)
    
    ip_encode = get_ip_encode(addresses)
    os.system('rm /etc/haproxy/conf.d/%s*.cfg' % (server_type))
    if os.path.isfile('/etc/haproxy/conf.d/%s-%s.cfg' % (server_type,ip_encode)):
        os.system('/etc/haproxy/conf.d/%s-%s.cfg' % (server_type,ip_encode))
    f = open('/etc/haproxy/conf.d/%s-%s.cfg' % (server_type,ip_encode),'w')
    f.write(temp_ha)
    f.close()
    
    os.system('rm /etc/haproxy/haproxy.cfg')
    os.system("cat /etc/haproxy/haproxy.cfg.orig /etc/haproxy/conf.d/*.cfg >> /etc/haproxy/haproxy.cfg")
    os.system('/usr/sbin/service haproxy reload')
    sys.stdout.flush()
    sys.stderr.flush()
    
def my_func(event):
    # check to see what the children are now
    path = event.path
    addresses = zk.get_children(event.path)
    create_cgf(path,addresses)

def get_service_hash():
    with open('/var/ha_services.json') as data_file:    
         service_hash = json.load(data_file)
    zookeeper_path_list = []
    for server_type in service_hash.keys():
        #aws-east-development-trade-monitor
        temp = "/%s-%s-%s-%s-%s" % (datacenter,location,environment,slug,server_type)
        zookeeper_path_list.append(temp)
    return service_hash, zookeeper_path_list

def get_ip_encode(children):
    ip_encode = ''.join(list(children))
    ip_encode = base64.b64encode(ip_encode)
    return ip_encode
 
while True:
    service_hash, zookeeper_path_list = get_service_hash()
    for path in zookeeper_path_list:
        try:
            exists = zk.exists(path)
        except KazooException:
            exists = None
            zk = get_zk_conn()
        if exists:
            children = zk.get_children(path, watch=my_func)
            print path,children
            
            ip_encode = get_ip_encode(children)
            server_type = path.split('-')[4]
            if os.path.isfile('/etc/haproxy/conf.d/%s-%s.cfg' % (server_type,ip_encode))==False:
                create_cgf(path,list(children))
                
            
    sys.stdout.flush()
    sys.stderr.flush()
    time.sleep(.5)
