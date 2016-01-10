import zc.zk
from kazoo.client import KazooClient
import time
import json
import os
import sys
import psutil
import base64 
from pprint import pprint
import logging #https://kazoo.readthedocs.org/en/latest/basic_usage.html
logging.basicConfig()

"""
0) load zookeeper from file written by chef
1) get ip address from file
2) register server
3) If change in servers then rerun chef

How to fix sharding 

"haproxy":{"elasticsearch":"127.0.0.1:9200",
               "sentinal":"127.0.0.1:26379",
               "kafka":"127.0.0.1:9092",
               "zookeeper":"127.0.0.1:2181",
               "druidbroker":"127.0.0.1:8082"   
    },

1)     
"haproxy":[{"server_type": "elasticsearch",
            "address":"127.0.0.1",
            "port":"9200"
            "shard":"True"}
}\

2) Or for every server type, if not found then check if beciase of shard
   then issue solved.  This is prob the easiest
  



"""

# with open('ha_services.json') as data_file:    
#     service_hash = json.load(data_file)
#zk_host_list = '107.170.219.233'


running_in_pydev = 'PYDEV_CONSOLE_ENCODING' in os.environ
if running_in_pydev==False:
    SETTINGS_FILE='/root/.bootops.yaml'
    from yaml import load, dump
    from yaml import Loader, Dumper
    f = open(SETTINGS_FILE)
    parms = load(f, Loader=Loader)
    f.close()
    
    environment = parms['environment']
    location = parms['location']
    datacenter = parms['datacenter']
    slug = parms['slug']
    server_type = parms['server_type']
    settings_path = parms['settings_path']
    if os.path.isfile('/var/cluster_slug/.txt'):
        cluster_slug = open("/var/cluster_slug/.txt").readlines()[0].strip()
    else:
        cluster_slug = "nocluster"
    zk_host_list = open('/var/zookeeper_hosts.json').readlines()[0]
    zk_host_list = zk_host_list.split(',')
    for i in xrange(len(zk_host_list)):
        zk_host_list[i]=zk_host_list[i]+':2181' 
    zk_host_str = ','.join(zk_host_list)
else:
    environment = "development"
    location = "ny"
    datacenter = "do"
    slug = "forex"
    zk_host_str = "1-zookeeper-do-development-ny-forex.forexhui.com:2181"
    cluster_slug = "nocluster"
    settings_path = "/home/ubuntu/workspace/forex-settings"
    server_type = "monitor"

def get_zk_conn():
    zk = KazooClient(hosts=zk_host_str, read_only=True)
    zk.start()
    return zk
zk = get_zk_conn()

def create_cgf(path,addresses):
    
    server_type = path.split('-')[3]
    if service_hash[server_type]["port"]==80:
        mode = 'http'
    else:
        mode = 'tcp'
    print server_type
    temp = []
    for index,ip in enumerate(list(addresses)):
        temp.append('server %s-%s %s:%s check' % (server_type,index+1,ip,service_hash[server_type]["port"]))
    temp = '\n'.join(temp)
    temp_ha = """
    listen %s  %s:%s
    mode %s
    option tcpka
    option tcplog
    balance roundrobin
    %s
    """ % (server_type,service_hash[server_type]['host'],service_hash[server_type]['port'],mode,temp)
    
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
    print "reloading haproxy"
    sys.stdout.flush()
    sys.stderr.flush()
    
def my_func(event):
    # check to see what the children are now
    path = event.path
    addresses = zk.get_children(event.path)
    create_cgf(path,addresses)

def get_service_hash(settings_path,server_type):
    fn = "%s/server_data_bag/%s.json" % (settings_path,server_type)
    with open(fn) as data_file:    
         service_hash = json.load(data_file)
    
    if service_hash.has_key('haproxy'):
        service_hash = service_hash['haproxy']
    else:
        service_hash = {}

    zookeeper_path_list = []
    for server_type in service_hash.keys():
        base = "%s-%s-%s-%s-%s" % (datacenter,environment,location,server_type,slug)
        if cluster_slug!="nocluster":
            base = "%s-%s" % (base,cluster_slugcluster_slug)
        zookeeper_path_list.append(base)

    return service_hash, zookeeper_path_list

def get_ip_encode(children):
    ip_encode = ''.join(list(children))
    ip_encode = base64.b64encode(ip_encode)
    return ip_encode
 
while True:
    service_hash, zookeeper_path_list = get_service_hash(settings_path,server_type)
    print 'mymeta',service_hash, zookeeper_path_list
    for path in zookeeper_path_list:
        try:
            exists = zk.exists(path)
        except KazooException:
            exists = None
            zk = get_zk_conn()
        print path,exists
        if exists:
            children = zk.get_children(path, watch=my_func)
            ip_encode = get_ip_encode(children)
            server_type = path.split('-')[3]

            if os.path.isfile('/etc/haproxy/conf.d/%s-%s.cfg' % (server_type,ip_encode))==False:
                create_cgf(path,list(children))
                
    sys.stdout.flush()
    sys.stderr.flush()
    print '-'*20
    time.sleep(1)
