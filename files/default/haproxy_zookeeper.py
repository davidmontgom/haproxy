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
import hashlib
import string
import glob
import subprocess
from pytz import timezone
import pytz
import datetime
from datetime import timedelta
from pprint import pprint
import logging #https://kazoo.readthedocs.org/en/latest/basic_usage.html
logging.basicConfig()
from bootops.classes import getparms





"""
[WARNING] 055/173408 (19627) : parsing [/etc/haproxy/haproxy.cfg:79] : a 'http-request' rule placed after a 'redirect' rule will still be processed before.
[WARNING] 055/173408 (19627) : parsing [/etc/haproxy/haproxy.cfg:80] : a 'http-request' rule placed after a 'redirect' rule will still be processed before.
[WARNING] 055/173408 (19627) : Setting tune.ssl.default-dh-param to 1024 by default, if your workload permits it you should set it to at least 2048. Please set a value >= 1024 to make this warning disappear.


"""

running_in_pydev = 'PYDEV_CONSOLE_ENCODING' in os.environ

parms = getparms.get_parms()
environment = parms['environment']
location = parms['location']
datacenter = parms['datacenter']
slug = parms['slug']['slug']
settings_path = parms['settings_path']

if running_in_pydev==False:
    debug = False
    this_server_type = parms['server_type']
    if os.path.isfile('/var/cluster_slug.txt'):
        cluster_slug = open("/var/cluster_slug.txt").readlines()[0].strip()
    else:
        cluster_slug = "nocluster"
else:
    cluster_slug = 'dccom'
    this_server_type = "haproxy"
    debug = True

print datacenter,environment,location




"""
use of clusterslug is required for all haproxy servers

if emperor=True then haproxy will redirect to multiple backends based in domains


match_type:
    backend servers cant use cluster slug
    haproxy must use the custer_slug of the backend server_type 
"""
def get_ip_encode(children):

    ip_encode = ''.join(list(children))
    ip_encode = base64.b64encode(ip_encode)
    
    return ip_encode

def get_zk_host_list():
    
    zk_host_list_dns = open('/var/zookeeper_hosts.json').readlines()[0]
    zk_host_list_dns = zk_host_list_dns.split(',')
    zk_host_list = []
    for aname in zk_host_list_dns:
        if aname.count('.')!=3:
            print 'aname:',aname
            try:
                data =  dns.resolver.query(aname, 'A')
                zk_host_list.append(data[0].to_text()+':2181')
            except:
                print 'ERROR, dns.resolver.NXDOMAIN',aname
                #zk_host_list.append('192.81.208.58:2181')
        else:
            zk_host_list.append(aname)
            
            
    return zk_host_list

def get_zk_host_str(zk_host_list):
    zk_host_str = ','.join(zk_host_list)
    return zk_host_str

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

def get_type():
    
    if this_server_type=='haproxy':
        haproxy_server = parms['haproxy']['haproxy']
        if parms['haproxy']['haproxy'].has_key(cluster_slug):
            if parms['haproxy']['haproxy'][cluster_slug].has_key('emperor'):
                emperor = parms['haproxy']['haproxy'][cluster_slug]['emperor']
            else:
                emperor = False
        else:
            emperor = False
        if parms['haproxy']['haproxy'].has_key(cluster_slug):
            if parms['haproxy']['haproxy'][cluster_slug].has_key("match_type"):
                match_type = parms['haproxy']['haproxy'][cluster_slug]["match_type"]
            else:
                match_type = None
    else:
        emperor = False
        match_type = None
    return emperor, match_type

class letsencrypt(object):
    
    def __init__(self,emperor_hash):
        
        self.emperor_hash = emperor_hash
        self.EXPIRE_THRESHOLD = 5
        
    def get_domain_list(self):
        
        self.domain_list = []
        for server_type,meta in self.emperor_hash.iteritems():
            for domain_hash in meta['domain']:
                domain = domain_hash.keys()[0]
                self.domain_list.append(domain)
                
                
        return self.domain_list
                
    def create(self):
        
        d = '-d '.join(self.domain_list)
        
        cmd = """
        /opt/letsencrypt/letsencrypt-auto --email admin@example.com --agree-tos --renew-by-default \
                                          --standalone --standalone-supported-challenges http-01 certonly \
                                          %s 
        """ % (d)
        
    def update(self):
        
        """
          /opt/letsencrypt/letsencrypt-auto --email admin@example.com --agree-tos --renew-by-default \
                                          --standalone --standalone-supported-challenges http-01 certonly \
                                          -d www3.debt-consolidation.com 
        
        """
        
        # dccom-development.govspring.com
        # http://www3.debt-consolidation.com/
        d = '-d '.join(self.domain_list)
         
        cmd = """
        /opt/letsencrypt/letsencrypt-auto --email admin@example.com --agree-tos --renew-by-default \
                                          --standalone --standalone-supported-challenges http-01 --http-01-port 9999 certonly \
                                          -d www3.debt-consolidation.com 

        """  % (d)
        
    def get_existing_haproxy_ssl_domains(self):
        
        ssl_files = []
        for name in glob.glob('/etc/haproxy/ssl/*'):
            ssl_files.append(name.split('/')[-1])
            
        self.ssl_files = ssl_files
        return ssl_files
    
    def get_existing_letsencrypt_ssl_domains(self):
        
        letsencrypt_dirs = []
        for name in glob.glob('/etc/letsencrypt/live/*'):
             letsencrypt_dirs.append(name.split('/')[-1])
            
        return  letsencrypt_dirs
    
    def create_and_move_pem_to_ssl(self,domain):
        #cat /etc/letsencrypt/live/www3.debt-consolidation.com/{fullchain.pem,privkey.pem} > /etc/haproxy/ssl/www3.debt-consolidation.com.pem
        cmd = """cat /etc/letsencrypt/live/%s/{fullchain.pem,privkey.pem} > /etc/haproxy/ssl/%s.pem""" % domain
        os.system(cmd)
    
    def get_ssl_exists(self,domain):
        
        ssl_files = self.get_existing_haproxy_ssl_domains()
        if domain in ssl_files:
            return True
        else:
            return False
    
    def get_domain_expire_date_hash(self):
        
        """
        easy_install pyopenssl
        notAfter=May 27 02:03:00 2016 GMT
        """
        
        domain_expire_hash = {}
        for domain in ssl_files:
            cmd = "openssl x509 -enddate -noout -in /etc/haproxy/ssl/%s " % domain
            p = subprocess.Popen(cmd, shell=True,stderr=subprocess.STDOUT,stdout=subprocess.PIPE,executable="/bin/bash")
            out = p.stdout.readline().strip()
            out = out.split('=')[1][:-4]
            expire_date = datetime.datetime.strptime(out, "%b %d %H:%M:00 %Y")
            days_left = (datetime.datetime.now()-expire).days
            domain_expire_hash[domain] = days_left
            
        return domain_expire_hash
        
    def haproxy_master_push(self,haproxy_server_list):
        
        """
        I am master and I will push to slaves on renew\
        to /etc/haproxy/ssl
        
        """
        
        pass
        
        
            
    def run(self):
        
        """
        if domain not in letsencrypt -> create
        
        openssl x509 -enddate -noout -in file.pem
        
        """
        
        
        pass
        
class haproxy(object):
    
    def __init__(self,parms,server_type,emperor=False,match_type=None,
                 cluster_slug='nocluster',base_list=[],emperor_hash={},base_ip_hash={},debug=False):
        
        self.parms = parms
        self.base_list = base_list
        self.emperor_hash = emperor_hash
        self.base_ip_hash = base_ip_hash
        self.emperor = emperor
        self.match_type = match_type
        self.environment = parms['environment']
        self.location = parms['location']
        self.datacenter = parms['datacenter']
        self.slug = parms['slug']['slug']
        self.cluster_slug = cluster_slug
        if server_type=='haproxy':
            self.haproxy_meta = self.parms[server_type]['haproxy'][cluster_slug]
        else:
            self.haproxy_meta = self.parms[server_type]['haproxy']
            
        self.debug = debug
        
    def create_service_frontend(self):
        
        temp_ha_list = []
        for server_type, meta in self.haproxy_meta.iteritems():
            
            mode = meta['mode']
            if meta.has_key('proxy_port'):
                proxy_port = meta['proxy_port']
            else:
                proxy_port = meta['remote_port']
            remote_port = meta['remote_port']
            host = meta['host']

            replace_values = { 'server_type':server_type,'mode':mode,'proxy_port':proxy_port,'remote_port':remote_port,'host':host}
            t = string.Template("""
            frontend ${server_type}_front
               bind ${host}:${proxy_port}
               mode $mode
               option ${mode}log
               default_backend ${server_type}_backend

            """)
            temp_ha = t.substitute(replace_values)
            temp_ha_list.append(temp_ha)
            
            if meta.has_key('frontend'):
                mode = meta['frontend']['mode']
                if meta['frontend'].has_key('proxy_port'):
                    proxy_port = meta['frontend']['proxy_port']
                else:
                    proxy_port = meta['frontend']['remote_port']
                remote_port = meta['frontend']['remote_port']
                host = meta['frontend']['host']
    
                replace_values = { 'server_type': meta['frontend']['name'],'mode':mode,'proxy_port':proxy_port,'remote_port':remote_port,'host':host}
                t = string.Template("""
                frontend ${server_type}_front
                   bind ${host}:${proxy_port}
                   mode $mode
                   option ${mode}log
                   default_backend ${server_type}_backend
    
                """)
                temp_ha = t.substitute(replace_values)
                temp_ha_list.append(temp_ha)

        temp_ha = '\n' .join(temp_ha_list)

        return temp_ha
   
    def create_service_backed(self,base_ip_hash):
        
        temp_ha_list = []
        for server_type, meta in self.haproxy_meta.iteritems():
            
            mode = meta['mode']
            if meta.has_key('proxy_port'):
                proxy_port = meta['proxy_port']
            else:
                proxy_port = meta['remote_port']
            remote_port = meta['remote_port']
            host = meta['host']
            
            if meta.has_key('services') and meta['services']==True:
                use_services = 'services/'
            else:
                use_services = ''
            
            if server_type.find('-')>=0:
                server_type_pure,cluster_slug = server_type.split('-')
                base = "%s%s-%s-%s-%s-%s-%s" % (use_services,server_type_pure,self.slug,self.datacenter,self.environment,self.location,cluster_slug)
            else:
                server_type_pure =server_type
                base = "%s%s-%s-%s-%s-%s" % (use_services,server_type_pure,self.slug,self.datacenter,self.environment,self.location)
            base = base.strip()
            temp = []
            
            #This is becuase haproxh fails if no backend even if no servers
            if base_ip_hash.has_key(base)==False:
                replace_values = { 'server_type':server_type,'mode':mode}
                t = string.Template("""
                backend ${server_type}_backend
                   mode $mode
                   option ${mode}log
                   balance roundrobin 
                """)
                temp_ha = t.substitute(replace_values)
                temp_ha_list.append(temp_ha)
                
                if meta.has_key('frontend'):
                    mode = meta['frontend']['mode']
                    if meta['frontend'].has_key('proxy_port'):
                        proxy_port = meta['frontend']['proxy_port']
                    else:
                        proxy_port = meta['frontend']['remote_port']
                    remote_port = meta['frontend']['remote_port']
                    host = meta['frontend']['host']
 
                    replace_values = { 'server_type': meta['frontend']['name'],'mode':mode}
                    t = string.Template("""
                    backend ${server_type}_backend
                       mode $mode
                       option ${mode}log
                       balance roundrobin
                    """)
                    temp_ha = t.substitute(replace_values)
                    temp_ha_list.append(temp_ha)
                
            if base_ip_hash.has_key(base):
                for index,ip in enumerate(list(base_ip_hash[base])):
                    temp.append('server %s-%s %s:%s check' % (server_type,index+1,ip,remote_port))   
                temp = '\n'.join(temp)
                
                replace_values = { 'server_type':server_type,'mode':mode,'server_list':temp}
                t = string.Template("""
                backend ${server_type}_backend
                   mode $mode
                   option ${mode}log
                   balance roundrobin
                   $server_list
                """)
                temp_ha = t.substitute(replace_values)
                temp_ha_list.append(temp_ha)
                
                if meta.has_key('frontend'):
                    mode = meta['frontend']['mode']
                    if meta['frontend'].has_key('proxy_port'):
                        proxy_port = meta['frontend']['proxy_port']
                    else:
                        proxy_port = meta['frontend']['remote_port']
                    remote_port = meta['frontend']['remote_port']
                    host = meta['frontend']['host']
                    
                    temp = []
                    for index,ip in enumerate(list(base_ip_hash[base])):
                        temp.append('server %s-%s %s:%s check' % (server_type,index+1,ip,remote_port))   
                    temp = '\n'.join(temp)
 
                    replace_values = { 'server_type': meta['frontend']['name'],'mode':mode,'server_list':temp}
                    t = string.Template("""
                    backend ${server_type}_backend
                       mode $mode
                       option ${mode}log
                       balance roundrobin
                       $server_list
                    """)
                    temp_ha = t.substitute(replace_values)
                    temp_ha_list.append(temp_ha)

        temp_ha = '\n' .join(temp_ha_list)

        return temp_ha

    def create_match_type_frontend_http(self):
    
        self.haproxy_meta
        server_type = self.haproxy_meta['match_type']
        mode = self.haproxy_meta['mode']
        proxy_port = self.haproxy_meta['proxy_port']
        remote_port = self.haproxy_meta['remote_port']
        host = self.haproxy_meta['host']
        
        replace_values = { 'server_type':server_type,'mode':mode,'proxy_port':proxy_port,'remote_port':remote_port,'host':host}
        t = string.Template("""
        frontend ${server_type}_front
           bind ${host}:${proxy_port}
           mode $mode
           option ${mode}log
           default_backend ${server_type}_backend
        """)
        temp_ha = t.substitute(replace_values)  
        
        return temp_ha
    
    def create_match_type_frontend_ssl(self): 
        
        self.haproxy_meta
        server_type = self.haproxy_meta['match_type']
        if self.haproxy_meta.has_key("ssl")==False:
            ssl = False
        else:
            ssl = self.haproxy_meta["ssl"]
            
        if ssl:
            replace_values = { 'server_type':server_type }
            t = string.Template("""
            
            frontend ${server_type}_https
    
               bind 0.0.0.0:443 ssl crt /etc/haproxy/ssl/
               reqadd X-Forwarded-Proto:\ https
               acl letsencrypt-request path_beg -i /.well-known/acme-challenge/
               use_backend letsencrypt if letsencrypt-request
               default_backend ${server_type}_backend
               
            backend letsencrypt
               mode http
               server letsencrypt 127.0.0.1:9999

    
            """)
            temp_ha = t.substitute(replace_values) 
        else:
            temp_ha = ''
            
        
        return temp_ha
    
    def create_match_type_web_backed(self,server_list): 
        
        self.haproxy_meta
        server_type = self.haproxy_meta['match_type']
        mode = self.haproxy_meta['mode']
        proxy_port = self.haproxy_meta['proxy_port']
        remote_port = self.haproxy_meta['remote_port']
        host = self.haproxy_meta['host']
        
        temp = []
        for index,ip in enumerate(list(server_list)):
            temp.append('server %s-%s %s:%s check cookie s%s' % (server_type,index+1,ip,remote_port,index+1))   
        temp = '\n'.join(temp)
        
        replace_values = { 'server_type':server_type,'mode':mode,'server_list':temp,'proxy_port':proxy_port,'remote_port':remote_port,'host':host}
        t = string.Template("""

        backend ${server_type}_backend
           option httpclose
           option forwardfor
           redirect scheme https if !{ ssl_fc }
           http-request set-header X-Forwarded-Port %[dst_port]
           http-request add-header X-Forwarded-Proto https if { ssl_fc }
           
           cookie SERVERID insert indirect nocache
           mode $mode
           option ${mode}log
           balance roundrobin
           $server_list
        """)
        temp_ha = t.substitute(replace_values) 
        
        return temp_ha
    
    def create_emperor_frontend_http(self,emperor_hash):
    
        server_type_app_hash = {}
        
        acl_string = ''
        for server_type,meta in emperor_hash.iteritems():
            print server_type,meta['domain']
            for domain_hash in meta['domain']:
                domain = domain_hash.keys()[0]
                acl_string = acl_string + 'acl %s hdr(host) -i %s' % (server_type, domain) + '\n'
            
        backend_string = ''
        for server_type,meta in emperor_hash.iteritems():
            backend_string = backend_string + 'use_backend %s_backend if %s' % (server_type,server_type) + '\n'
       
        t = """
frontend public

    # Listen on port 80
    bind *:80
    mode http
    
    # Define ACLs for each domain
    %s
    
    # Figure out which backend (= VM) to use
    %s
        
        """ % (acl_string,backend_string)
    
        return t
        
    def create_emperor_frontend_ssl(self,emperor_hash):
        
        domain_server_type_hash = [{'domain':'dashboard.feed-galaxy.com','server_type':'frontend'}]
        
  
        frontend_list = []
        for server_type,meta in emperor_hash.iteritems():
            for domain_hash in meta['domain']:
                domain = domain_hash.keys()[0]
                temp = """acl host_%s hdr(host) -i %s""" % (server_type,domain)
                frontend_list.append(temp)
        acl = '\n'.join(frontend_list)
        
        frontend_list = []
        for server_type in emperor_hash.keys():
            temp = """use_backend  %s_backend if host_%s""" % (server_type,server_type)
            frontend_list.append(temp)
        use_backend = '\n'.join(frontend_list)
            
        
        self.https_frontend = """
frontend in_https

   bind 0.0.0.0:443 ssl crt /etc/haproxy/ssl/
   reqadd X-Forwarded-Proto:\ https
   acl letsencrypt-request path_beg -i /.well-known/acme-challenge/
   use_backend letsencrypt if letsencrypt-request
   
   %s
   %s
           """ % (acl,use_backend)
    
 
        self.https_frontend = """
        %s
        
        backend letsencrypt
               mode http
               server letsencrypt 127.0.0.1:9999
        """ % (self.https_frontend)   

        
        return self.https_frontend
        
    def create_emperor_web_backed(self,emperor_hash,base_ip_hash): 
        
        remote_port = 80
        proxy_port = 80
        mode = 'http'
        temp_ha = []

        for server_type,meta in emperor_hash.iteritems():
    
            base = meta['base']
            if base_ip_hash.has_key(base):
                server_list = base_ip_hash[base] 
                temp = []
                if server_list:
                    for index,ip in enumerate(list(server_list)):
                        temp.append('server %s-%s %s:%s check cookie s%s' % (server_type,index+1,ip,remote_port,index+1))   
                    temp = '\n'.join(temp)
                else:
                    temp = None
                
                if temp:
                    replace_values = { 'server_type':server_type,'mode':mode,'server_list':temp,'proxy_port':proxy_port,'remote_port':remote_port}
                else:
                    replace_values = { 'server_type':server_type,'mode':mode,'server_list':'','proxy_port':proxy_port,'remote_port':remote_port}
                    
                t = string.Template("""
                    
                backend ${server_type}_backend
                   option httpclose
                   option forwardfor
                   http-request set-header X-Forwarded-Port %[dst_port]
                   http-request add-header X-Forwarded-Proto https if { ssl_fc }
                   
                   cookie SERVERID insert indirect nocache
                   mode $mode
                   option ${mode}log
                   balance roundrobin
                   $server_list
                """)
                temp_ha.append(t.substitute(replace_values))


        temp_ha = '\n'.join(temp_ha)
        return temp_ha
        
    def get_zk_base_servers(self,base_list):
        
        base_ip_hash = {}
        if self.debug == False:
            for base in base_list:
                path = '/%s/' % base
                exists = self.zk.exists(path)
                if exists:
                    children = self.zk.get_children(path, watch=my_func)
                    #ip_encode = get_ip_encode(children)
                    base_ip_hash[base]=list(children)
        else:
            #base_ip_hash['frontend-seo-aws-development-east-dccom']=['127.0.0.1','127.0.0.2']
            base_ip_hash['sentinel-feed-do-cloud-ny'] = ['111.111.111.111']
            base_ip_hash['elasticsearch-feed-do-cloud-ny'] = ['222.111.111.111']
        return base_ip_hash 
        
    def get_emperor_hash(self):

        emperor_hash = {}
        for server_type, meta in self.parms.iteritems():
            if isinstance(meta, dict):
                if meta.has_key(self.datacenter):
                    if meta[self.datacenter].has_key(self.environment):
                        if meta[self.datacenter][self.environment].has_key(self.location):
                            #print meta[datacenter][environment][location].keys()
                            for cs in meta[self.datacenter][self.environment][self.location].keys():
                                if isinstance(meta[self.datacenter][self.environment][self.location][cs], dict):
                                    if meta[self.datacenter][self.environment][self.location][cs].has_key("emperor_domain"):
                                        temp = '%s-%s' % (server_type,cs)
                                        emperor_hash[temp] = {}
                                        if cs=='nocluster':
                                            base = "%s-%s-%s-%s-%s" % (server_type,self.slug,self.datacenter,self.environment,self.location)
                                        else:
                                            base = "%s-%s-%s-%s-%s-%s" % (server_type,self.slug,self.datacenter,self.environment,self.location,cs)
                                        emperor_hash[temp]['base']=base
                                        emperor_hash[temp]['domain']=meta[self.datacenter][self.environment][self.location][cs]["emperor_domain"]
                                        
        return emperor_hash
        
    def add_backend_letsencrypt(self):
        
        self.letsencrypt_backend = """
                backend letsencrypt
                   mode http
                   server letsencrypt 127.0.0.1:9999
               """
        return self.letsencrypt_backend
  
    def generate(self):
        
        is_reload = False
        if self.emperor:
            front_end_config_http = self.create_emperor_frontend_http(self.emperor_hash)
            front_end_confg_ssl = self.create_emperor_frontend_ssl(self.emperor_hash)
            backend_config = self.create_emperor_web_backed(self.emperor_hash,self.base_ip_hash)
#             print front_end_config_http
#             print front_end_confg_ssl
#             print backend_config
            
            ha_proxy_config = """
            %s
            %s
            %s
            """ % (front_end_config_http,front_end_confg_ssl,backend_config)

            
            #check for change
            haproxy_encode = hashlib.md5(ha_proxy_config).hexdigest()
            reload = False
            if self.debug==False:
                if  os.path.isfile('/etc/haproxy/conf.d/ha_enocde_%s' % haproxy_encode)==False:
                    os.system('rm /etc/haproxy/conf.d/ha_enocde_*')
                    os.system('touch /etc/haproxy/conf.d/ha_enocde_%s' % haproxy_encode)
                    f = open('/etc/haproxy/conf.d/emperor.cfg','w')
                    f.write(ha_proxy_config)
                    f.close()
                    reload = True
                
                if reload:
                    os.system('rm /etc/haproxy/haproxy.cfg')
                    os.system("cat /etc/haproxy/haproxy.cfg.orig /etc/haproxy/conf.d/emperor.cfg >> /etc/haproxy/haproxy.cfg")
                    os.system('/usr/sbin/service haproxy reload')
                    print "reloading haproxy"

        elif self.match_type:
            if self.base_ip_hash:
                server_list = self.base_ip_hash[self.base_list[0]]
                front_end_config_http = self.create_match_type_frontend_http()
                front_end_confg_ssl = self.create_match_type_frontend_ssl()
                backend_config = self.create_match_type_web_backed(server_list)
#                 print front_end_config_http
#                 print front_end_confg_ssl
#                 print backend_config
                ha_proxy_config = """
                %s
                %s
                %s
                """ % (front_end_config_http,front_end_confg_ssl,backend_config)
                print ha_proxy_config
                 #check for change
                haproxy_encode = hashlib.md5(ha_proxy_config).hexdigest()
                reload = False
                if self.debug==False:
                    if  os.path.isfile('/etc/haproxy/conf.d/ha_enocde_%s' % haproxy_encode)==False:
                        os.system('rm /etc/haproxy/conf.d/ha_enocde_*')
                        os.system('touch /etc/haproxy/conf.d/ha_enocde_%s' % haproxy_encode)
                        f = open('/etc/haproxy/conf.d/match_type.cfg','w')
                        f.write(ha_proxy_config)
                        f.close()
                        reload = True
                    
                    if reload:
                        os.system('rm /etc/haproxy/haproxy.cfg')
                        os.system("cat /etc/haproxy/haproxy.cfg.orig /etc/haproxy/conf.d/match_type.cfg >> /etc/haproxy/haproxy.cfg")
                        os.system('/usr/sbin/service haproxy reload')
                        print "reloading haproxy"
        else:
            print 'backend services'
            front_end_config = self.create_service_frontend()
            backend_config = self.create_service_backed(self.base_ip_hash)
            #print front_end_config
            #print backend_config
            ha_proxy_config = """
                %s
                %s
                """ % (front_end_config,backend_config)
            if self.debug==True:
                print ha_proxy_config
            haproxy_encode = hashlib.md5(ha_proxy_config).hexdigest()
            reload = False
            if self.debug==False:
                if  os.path.isfile('/etc/haproxy/conf.d/ha_enocde_%s' % haproxy_encode)==False:
                    os.system('rm /etc/haproxy/conf.d/ha_enocde_*')
                    os.system('touch /etc/haproxy/conf.d/ha_enocde_%s' % haproxy_encode)
                    f = open('/etc/haproxy/conf.d/service.cfg','w')
                    f.write(ha_proxy_config)
                    f.close()
                    reload = True
                
                if reload:
                    os.system('rm /etc/haproxy/haproxy.cfg')
                    os.system("cat /etc/haproxy/haproxy.cfg.orig /etc/haproxy/conf.d/service.cfg >> /etc/haproxy/haproxy.cfg")
                    os.system('/usr/sbin/service haproxy reload')
                    print "reloading haproxy"

def get_emperor_hash():
    
    emperor_hash = {}
    for server_type, meta in parms.iteritems():
        if isinstance(meta, dict):
            if meta.has_key(datacenter):
                if meta[datacenter].has_key(environment):
                    if meta[datacenter][environment].has_key(location):
                        #print meta[datacenter][environment][location].keys()
                        for cs in meta[datacenter][environment][location].keys():
                            if isinstance(meta[datacenter][environment][location][cs], dict):
                                if meta[datacenter][environment][location][cs].has_key("emperor_domain"):
                                    test = meta[datacenter][environment][location][cs]["emperor_domain"]
                                    
                                    if test['cluster_slug']==cluster_slug:
 
                                        temp = '%s-%s' % (server_type,cs)
                                        emperor_hash[temp] = {}
                                        if cs=='nocluster':
                                            base = "%s-%s-%s-%s-%s" % (server_type,slug,datacenter,environment,location)
                                        else:
                                            base = "%s-%s-%s-%s-%s-%s" % (server_type,slug,datacenter,environment,location,cs)
                                        emperor_hash[temp]['base']=base
                                        emperor_hash[temp]['domain']=meta[datacenter][environment][location][cs]["emperor_domain"]["domains"]
               
    return emperor_hash

def get_base_list():
    
    base_list = []
    if match_type:
        server_type = match_type
        base = "%s-%s-%s-%s-%s" % (server_type,slug,datacenter,environment,location)
        base_list = [base]
    elif emperor:
        emperor_hash = get_emperor_hash()
        for key,meta in emperor_hash.iteritems():
            base_list.append(meta['base'])
    else:
        for key,meta in parms[this_server_type]['haproxy'].iteritems():
            
            # Use e.g. RDS postgre or mysql or redis
            if meta.has_key('services') and meta['services']==True:
                use_services = 'services/'
            else:
                use_services = ''
                
            
            if key.find('-')>=0:
                server_type,cs = key.split('-')
                base = "%s%s-%s-%s-%s-%s-%s" % (use_services,server_type,slug,datacenter,environment,location,cs)
            else:
                server_type = key
                base = "%s%s-%s-%s-%s-%s" % (use_services,server_type,slug,datacenter,environment,location)
            base_list.append(base.strip())
    return base_list

def my_func(event):
    # check to see what the children are now
    emperor, match_type = get_type()
    if emperor:
        emperor_hash = get_emperor_hash()
    else:
        emperor_hash = {}
    base_list = get_base_list()
    base_ip_hash = {}
    for base in base_list:
        path = '/%s/' % base
        exists = zk.exists(path)
        if exists:
            address = zk.get_children(path)
            base_ip_hash[base]=list(address)
    ha = haproxy(parms,this_server_type,emperor,match_type,cluster_slug,base_list,emperor_hash,base_ip_hash,debug)
    ha.generate()
    


emperor, match_type = get_type()
print 'emperor:',emperor
print 'match_type:',match_type
print 'cluster_slug',cluster_slug
print 'this_server_type:',this_server_type



# emperor_hash = get_emperor_hash()
# pprint(emperor_hash)
# exit()
# base_list = get_base_list()
# print base_list




zk = get_zk_conn()
zk_chksum_init = hashlib.md5(open('/var/zookeeper_hosts.json', 'rb').read()).hexdigest()


"""
Firgure a way to graceful reload if options change but servers do not
emporor - use a custer_list hash "emperor_domain": ["www3.debt-consolidation.com"],
"emperor_domain": [{"domain":"www3.debt-consolidation.com","cluster_slug":"frontend"}],

work on ssl coldstart
"""

while True:

    zk_chksum = hashlib.md5(open('/var/zookeeper_hosts.json', 'rb').read()).hexdigest()
    if zk_chksum!=zk_chksum_init:
        zk = get_zk_conn()
        

    base_list = get_base_list()
    for base in base_list:
        path = '/%s/' % base
        exists = zk.exists(path)
        if exists:
            children = zk.get_children(path, watch=my_func)
            print path, children
       
            
    reload = False
    if emperor:
        if os.path.isfile('/etc/haproxy/conf.d/emperor.cfg')==False:
            reload = True
    if match_type:
        if os.path.isfile('/etc/haproxy/conf.d/match_type.cfg')==False:
            reload = True
    if not emperor and not match_type:
        if os.path.isfile('/etc/haproxy/conf.d/service.cfg')==False:
            reload = True
      

    if reload:
        if emperor:
            emperor_hash = get_emperor_hash()
        else:
            emperor_hash = {}
        base_list = get_base_list()
        base_ip_hash = {}
        for base in base_list:
            path = '/%s/' % base
            exists = zk.exists(path)
            if exists:
                address = zk.get_children(path)
                base_ip_hash[base]=list(address)
                
        
        ha = haproxy(parms,this_server_type,emperor,match_type,cluster_slug,base_list,emperor_hash,base_ip_hash,debug)
        ha.generate()
        
            
    sys.stdout.flush()
    sys.stderr.flush()
    print '-'*20
    time.sleep(1)





