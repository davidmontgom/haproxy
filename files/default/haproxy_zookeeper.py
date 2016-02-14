import zc.zk
from kazoo.client import KazooClient
import dns.resolver 
import hashlib
import time
import json
import os
import sys
import psutil
import base64 
import string
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


"""
haproxy name server_type-cluster_slug

"""

zk_chksum_init = hashlib.md5(open('/var/zookeeper_hosts.json', 'rb').read()).hexdigest()

def get_zk_host_list():
    zk_host_list_dns = open('/var/zookeeper_hosts.json').readlines()[0]
    zk_host_list_dns = zk_host_list_dns.split(',')
    zk_host_list = []
    for aname in zk_host_list_dns:
        try:
            data =  dns.resolver.query(aname, 'A')
            zk_host_list.append(data[0].to_text()+':2181')
        except:
            print 'ERROR, dns.resolver.NXDOMAIN',aname
    return zk_host_list

def get_zk_host_str(zk_host_list):
    zk_host_str = ','.join(zk_host_list)
    return zk_host_str


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
    this_server_type = parms['server_type']
    settings_path = parms['settings_path']
    if os.path.isfile('/var/cluster_slug.txt'):
        cluster_slug = open("/var/cluster_slug.txt").readlines()[0].strip()
    else:
        cluster_slug = "nocluster"
        
#     zk_host_list = open('/var/zookeeper_hosts.json').readlines()[0]
#     zk_host_list = zk_host_list.split(',')
#     for i in xrange(len(zk_host_list)):
#         zk_host_list[i]=zk_host_list[i]+':2181' 
#     zk_host_str = ','.join(zk_host_list)
else:
    environment = "development"
    location = "ny"
    datacenter = "do"
    slug = "forex"
    zk_host_str = "1-zookeeper-forex-do-development-ny.forexhui.com:2181"
    cluster_slug = "pixel"
    settings_path = "/home/ubuntu/workspace/forex-settings"
    this_server_type = "haproxy"

def get_zk_conn():
    zk_host_list = get_zk_host_list()
    if zk_host_list:
        zk_host_str = get_zk_host_str(zk_host_list)
        zk = KazooClient(hosts=zk_host_str, read_only=True)
        zk.start()
    else:
        zk = None
        print 'waiting for zk conn...'
        time.sleep(1)
    return zk
zk = get_zk_conn()



def create_cgf(path,addresses,server_type,meta):
    

    

    mode = meta['mode']
        
    if meta.has_key("proxy_port"):
        proxy_port = meta['proxy_port']
    else:
        proxy_port = meta['remote_port']
    remote_port = meta['remote_port']
    host = meta['host']
    
    if meta.has_key("sticky"):
        sticky = meta["sticky"]
    else:
        sticky = False
        
    #http://blog.haproxy.com/2012/03/29/load-balancing-affinity-persistence-sticky-sessions-what-you-need-to-know/
    temp = []
    if sticky==False:
        for index,ip in enumerate(list(addresses)):
            temp.append('server %s-%s %s:%s check' % (server_type,index+1,ip,remote_port))   
        temp = '\n'.join(temp)
    else:
        for index,ip in enumerate(list(addresses)):
            temp.append('server %s-%s %s:%s check cookie s%s' % (server_type,index+1,ip,remote_port,index+1))   
        temp = '\n'.join(temp)
        

    

    if sticky==False:
        replace_values = { 'server_type':server_type,'mode':mode,'server_list':temp,'proxy_port':proxy_port,'remote_port':remote_port,'host':host}
        t = string.Template("""
        frontend ${server_type}_front
           bind ${host}:${proxy_port}
           mode $mode
           option ${mode}log
           default_backend ${server_type}_backend
        
        backend ${server_type}_backend
           mode $mode
           option ${mode}log
           balance roundrobin
           $server_list
        """)
        temp_ha = t.substitute(replace_values)
    else:
        replace_values = { 'server_type':server_type,'mode':mode,'server_list':temp,'proxy_port':proxy_port,'remote_port':remote_port,'host':host}
        t = string.Template("""
        frontend ${server_type}_front
           bind ${host}:${proxy_port}
           mode $mode
           option ${mode}log
           default_backend ${server_type}_backend
        
        backend ${server_type}_backend
           option httpclose
           option forwardfor
           http-request set-header X-Forwarded-Port %[dst_port]
           http-request add-header X-Forwarded-Proto https if { ssl_fc }
           option httpchk HEAD / HTTP/1.1\r\nHost:localhost
           cookie SERVERID insert indirect nocache
           mode $mode
           option ${mode}log
           balance roundrobin
           $server_list
        """)
        temp_ha = t.substitute(replace_values)
        
    
    
    if meta.has_key('frontend'):
        
        fe_server_type = meta['frontend']['name']
        mode = meta['frontend']['mode']
        proxy_port = meta['frontend']['proxy_port']
        remote_port = meta['frontend']['remote_port']
        host = meta['frontend']['host']
        temp = []
        for index,ip in enumerate(list(addresses)):
            temp.append('server %s-%s-%s %s:%s check' % (fe_server_type,server_type,index+1,ip,remote_port))
        temp = '\n'.join(temp)
        replace_values = { 'server_type':fe_server_type,'mode':mode,'server_list':temp,'proxy_port':proxy_port,'remote_port':remote_port,'host':host}
        t = string.Template("""
        frontend ${server_type}_front
           bind ${host}:${proxy_port}
           mode $mode
           option ${mode}log
           default_backend ${server_type}_backend
        
        backend ${server_type}_backend
           mode $mode
           option ${mode}log
           balance roundrobin
           $server_list
        """)
        temp_ha_frontend = t.substitute(replace_values)
    
        temp_ha = """
        %s
        
        %s
        
        """ % (temp_ha,temp_ha_frontend)

    ip_encode = get_ip_encode(addresses)
    os.system('rm /etc/haproxy/conf.d/%s*.cfg' % (server_type))
    if os.path.isfile('/etc/haproxy/conf.d/%s-%s.cfg' % (server_type,ip_encode)):
        os.system('/etc/haproxy/conf.d/%s-%s.cfg' % (server_type,ip_encode))
    f = open('/etc/haproxy/conf.d/%s-%s.cfg' % (server_type,ip_encode),'w')
    f.write(temp_ha)
    f.close()
    
    f = open('/tmp/hareload.txt','a')
    f.write('%s %s\n' % (server_type,json.dumps(meta)))
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

    cluster_slugs_to_delete = []
    zookeeper_path_list = []
    for server_type_temp,meta in service_hash.iteritems():

        this_cluster_slug = "nocluster"
        if server_type_temp.find('-')>=0:
            server_type,this_cluster_slug = server_type_temp.split('-')
            service_hash[server_type_temp]['cluster_slug']=this_cluster_slug
        else:
            server_type = server_type_temp
            
  
        add = True
        
        #match type is for matching a ha proxy cluster_slug with a server_type ONLY
        if meta.has_key('match_type'):
            match_type = meta['match_type']
        else:
            match_type = False
            
        if match_type:
            if match_type==cluster_slug:
                add = True
            else:
                add = False
                cluster_slugs_to_delete.append(server_type_temp)
            

        if add==True:
            base = "%s-%s-%s-%s-%s" % (server_type,slug,datacenter,environment,location)
            if this_cluster_slug!="nocluster":
                base = "%s-%s" % (base,this_cluster_slug)
            service_hash[server_type_temp]['path']=base
            zookeeper_path_list.append(base)
            
    #Used for frontend HA.  Delete server_types that dont have
    # a match type.  Front end proxies will have ONLY 1 match type
    # assert error if len(service_hash)>1
    for server_type in cluster_slugs_to_delete:
        del service_hash[server_type]
        
    return service_hash, zookeeper_path_list

def get_ip_encode(children):
    ip_encode = ''.join(list(children))
    ip_encode = base64.b64encode(ip_encode)
    return ip_encode
 
while True:
    service_hash, zookeeper_path_list = get_service_hash(settings_path,this_server_type)
    print 'mymeta',service_hash, zookeeper_path_list
    
    zk_chksum = hashlib.md5(open('/var/zookeeper_hosts.json', 'rb').read()).hexdigest()
    if zk_chksum!=zk_chksum:
        zk = get_zk_conn()
        
    
    for server_type,meta in service_hash.iteritems():
        
        path = meta['path']

        try:
            exists = zk.exists(path)
        except KazooException:
            exists = None
            zk = get_zk_conn()
        #print path,exists
        if exists:
            children = zk.get_children(path, watch=my_func)
            #print children
            ip_encode = get_ip_encode(children)
               
            if os.path.isfile('/etc/haproxy/conf.d/%s-%s.cfg' % (server_type,ip_encode))==False:
                create_cgf(path,list(children),server_type,meta)
   
 
    sys.stdout.flush()
    sys.stderr.flush()
    print '-'*20
    time.sleep(1)
