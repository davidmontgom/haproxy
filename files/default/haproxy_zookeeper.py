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
import traceback







"""

EMPEROR

"haproxy-api": {
    "host": "0.0.0.0",
    "remote_port": 80,
    "proxy_port": 80,
    "mode": "http",
    "emperor": true
}


cluster slug test  --> "emperor_domain": {"cluster_slug":"api","ssl":true,"domains":[{"ass.iboot.io":{"null":false}}] },

cluster slug test2  --> "emperor_domain": {"cluster_slug":"api","ssl":true,"domains":[{"ass2.iboot.io":{"null":false}}] },


SERVICE








MATCH TYPE

emperor==False and the length of include==1

"haproxy-angular2": {
    "host": "0.0.0.0",
    "remote_port": 80,
    "proxy_port": 80,
    "mode": "http",
    "emperor": false,
    "ssl": false,
    "include": ["angular2-wltm"]
},

"""

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
    
    try:
        zk.stop()
    except:
        zk = None
    
    zk_host_list = get_zk_host_list()
    if zk_host_list:
        try:
            zk_host_str = get_zk_host_str(zk_host_list)
            zk = KazooClient(hosts=zk_host_str, read_only=True)
            zk.start()
        except:
            zk = None
    else:
        zk = None
        print 'waiting for zk conn...'
    return zk

class haproxy(object):
    
    """
    EXAMPLE 1 
    api with cluster_slug  server needs access to mysql and ES with same cluster slug
    
    api with cluster_slug  server needs access to mysql and ES with same cluster slug and redis with different
    
    
    """
    
    def __init__(self,server_type,cluster_slug,haproxy_server_params,slug,datacenter,environment,location):
        
       self.server_type = server_type
       self.cluster_slug = cluster_slug
       self.haproxy_server_params = haproxy_server_params
       self.slug=slug
       self.datacenter=datacenter
       self.environment=environment
       self.location=location
       
       self.reload = False
       self.active_proxies = []
       self.ha_front_end_blocks = []
       self.ha_backend_end_blocks = []
       self.base_ip_hash = {}
       
    def get_server_type(self,server_type_cs):
        """
        server_type = self.get_server_type(server_type_cs)
        """
        if server_type_cs.find('-')>=0:
            server_type = server_type_cs.split('-')[0]
        else:
            server_type = server_type_cs
        return server_type
    
    def get_cluster_slug(self,server_type_cs):
        if server_type_cs.find('-')>=0:
            cluster_slug = server_type_cs.split('-')[1]
        else:
            cluster_slug = 'nocluster'
        return cluster_slug

    def get_base_name_of_proxy_service(self,server_type_cs,use_services=''):
    
        if server_type_cs.find('-')>=0:
            server_type,cluster_slug = server_type_cs.split('-')
            base = "%s%s-%s-%s-%s-%s-%s" % (use_services,server_type,self.slug,self.datacenter,self.environment,self.location,cluster_slug)
        else:
            base = "%s%s-%s-%s-%s-%s" % (use_services,server_type_cs,self.slug,self.datacenter,self.environment,self.location)
        
        return base.strip()

    def create_proxy_service_list(self):
        
        """
        
        4 cases
        
        1) proxy server does not contain a cluster slug - result: service is added to every CS
        2) proxy server does not contain a cluster slug but with an exclude - result: all CS are added the proxy except those in the exclude list
        3) proxy server has a cluster slug and matches the CS - then added    
            e.g. an api sever might need access to 2 different mysql clusters
        4) proxy server does not have matching CS but forced with include 
        
        
        
        
        
        
        
        Ensure that given  a server, only eligable servers are proxied
        
        server_type = 'api'
        cluster_slug = 'health'
        
        
        haproxy_server_params = {
                         u'elasticsearch-openrx': {u'host': u'127.0.0.1',
                                                   u'mode': u'tcp',
                                                   u'proxy_port': 9203,
                                                   u'remote_port': 9200,
                                                   u'include':['aaa']},
                         u'elasticsearch-dude': {u'host': u'127.0.0.1',
                                                   u'mode': u'tcp',
                                                   u'proxy_port': 9203,
                                                   u'remote_port': 9200,
                                                   u'include':['health']},
                         u'mysql-health': {u'host': u'127.0.0.1',
                                                   u'mode': u'tcp',
                                                   u'proxy_port': 9203,
                                                   u'remote_port': 9200,
                                                   u'include':[]},
                         u'zookeeper': {u'host': u'127.0.0.1',
                                                   u'mode': u'tcp',
                                                   u'proxy_port': 9203,
                                                   u'remote_port': 9200,
                                                   u'include':[]},
                         u'kibana': {u'host': u'127.0.0.1',
                                                   u'mode': u'tcp',
                                                   u'proxy_port': 9203,
                                                   u'remote_port': 9200,
                                                   u'exclude':['health']}
                         
                         
                         }
                                 
        return [u'elasticsearch-dude', u'zookeeper', u'mysql-health']
        
        
        
        """
        
        active_proxies = []
        temp = self.haproxy_server_params.keys()
        for server_type_cs, meta in self.haproxy_server_params.iteritems():
            if server_type_cs.find('-')>=0:
                temp_cs = server_type_cs.split('-')[1]
                if temp_cs==self.cluster_slug:
                    active_proxies.append(server_type_cs)
                else:
                    if meta.has_key('include') and self.cluster_slug in meta['include']:
                        active_proxies.append(server_type_cs)
            else:
                #If no cluster_slug then included
                if meta.has_key('exclude') and self.cluster_slug in meta['exclude']:
                    pass 
                    #active_proxies.append(server_type_cs)
                else:
                    active_proxies.append(server_type_cs)
                    
                
                
        
        self.active_proxies = active_proxies
        return active_proxies

    def get_emperor_hash(self):

        emperor_hash = {}
        for server_type, meta in parms.iteritems():
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
        
        self.emperor_hash = emperor_hash                           
        return self.emperor_hash

    def create_service_frontend(self,server_type_cs,meta):
        
        mode = meta['mode']
        if meta.has_key('proxy_port'):
            proxy_port = meta['proxy_port']
        else:
            proxy_port = meta['remote_port']
        remote_port = meta['remote_port']
        host = meta['host']
        
        replace_values = { 'server_type':server_type_cs,'mode':mode,'proxy_port':proxy_port,'remote_port':remote_port,'host':host}
        t = string.Template("""
        frontend ${server_type}_front
           bind ${host}:${proxy_port}
           mode $mode
           option ${mode}log
           default_backend ${server_type}_backend
        
        """)
        temp_ha = t.substitute(replace_values)
        self.ha_front_end_blocks.append(temp_ha)
        if meta.has_key('frontend'):
            for frontend_server_type_cs,frontend_meta in meta['frontend'].iteritems():
                self.create_service_frontend(frontend_server_type_cs,frontend_meta)
                
    def create_service_backend(self,server_type_cs,meta):
        
            
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
            
        base = self.get_base_name_of_proxy_service(server_type_cs,use_services)
        temp = []
            
        #This is becuase haproxy fails if no backend even if no servers
        if self.base_ip_hash.has_key(base)==False:
            replace_values = { 'server_type':server_type_cs,'mode':mode}
            t = string.Template("""
            backend ${server_type}_backend
              mode $mode
              option ${mode}log
              balance roundrobin 
            """)
            temp_ha = t.substitute(replace_values)
            self.ha_backend_end_blocks.append(temp_ha)
            if meta.has_key('frontend'):
                for frontend_server_type_cs,frontend_meta in meta['frontend'].iteritems():
                    self.create_service_backend(frontend_server_type_cs,frontend_meta)
           
          
           
        if self.base_ip_hash.has_key(base):
            for index,ip in enumerate(list(self.base_ip_hash[base])):
                temp.append('server %s-%s %s:%s check' % (server_type_cs,index+1,ip,remote_port))   
            temp = '\n'.join(temp)
            
            replace_values = { 'server_type':server_type_cs,'mode':mode,'server_list':temp}
            t = string.Template("""
            backend ${server_type}_backend
               mode $mode
               option ${mode}log
               balance roundrobin
               $server_list
            """)
            temp_ha = t.substitute(replace_values)
            self.ha_backend_end_blocks.append(temp_ha)
            
            if meta.has_key('frontend'):
                for frontend_server_type_cs,frontend_meta in meta['frontend'].iteritems():
                    self.create_service_backend(frontend_server_type_cs,frontend_meta)
     
    def create_matchtype_frontend(self,meta):

        server_type_cs = meta['include'][0]
        mode = meta['mode']
        proxy_port = meta['proxy_port']
        remote_port = meta['remote_port']
        host = meta['host']
        
        acme1 = ' '
        acme2 = ' '
        if meta.has_key('ssl') and meta['ssl']==True:
            acme1 = 'acl url_acme_http01 path_beg /.well-known/acme-challenge/'
            acme2 = 'http-request use-service lua.acme-http01 if METH_GET url_acme_http01'
        
        replace_values = { 'server_type':server_type_cs,'mode':mode,'proxy_port':proxy_port,'remote_port':remote_port,'host':host, 'acme1':acme1, 'acme2':acme2}
        t = string.Template("""
        frontend ${server_type}_front
           ${acme1}
           ${acme2}
           bind ${host}:${proxy_port}
           mode $mode
           option ${mode}log
           default_backend ${server_type}_backend
        """)
        temp_ha = t.substitute(replace_values)  

        self.ha_front_end_blocks.append(temp_ha)
        return self.ha_front_end_blocks 
    
    def create_matchtype_backend(self,meta):
        
        server_type_cs = meta['include'][0]

        mode = meta['mode']
        proxy_port = meta['proxy_port']
        remote_port = meta['remote_port']
        host = meta['host']
        
        
        base = self.get_base_name_of_proxy_service(server_type_cs,use_services='')
        temp = []
        #This is becuase haproxy fails if no backend even if no servers
        if self.base_ip_hash.has_key(base)==False:
            temp=''
        else:
            for index,ip in enumerate(list(self.base_ip_hash[base])):
                temp.append('server %s-%s %s:%s check cookie s%s' % (server_type,index+1,ip,remote_port,index+1))   
            temp = '\n'.join(temp)
        

        if meta.has_key('use_ssl') and meta['use_ssl']==True:
            #proto_https = 'http-request add-header X-Forwarded-Proto https if { ssl_fc }'
            scheme_https = 'redirect scheme https if !{ ssl_fc }'
        else:
            scheme_https=''
            #proto_https=''
            
        
        replace_values = {'scheme_https':scheme_https,'server_type':server_type_cs,'mode':mode,'server_list':temp,'proxy_port':proxy_port,'remote_port':remote_port,'host':host}
        
        
        t = string.Template("""

        backend ${server_type}_backend
           option httpclose
           option forwardfor
           
           http-request set-header X-Forwarded-Port %[dst_port]
           http-request add-header X-Forwarded-Proto https if { ssl_fc }
           ${scheme_https}
           
           cookie SERVERID insert indirect nocache
           mode $mode
           option ${mode}log
           balance roundrobin
           $server_list
        """)
        temp_ha = t.substitute(replace_values) 
        
        self.ha_backend_end_blocks.append(temp_ha)
        
        
        return self.ha_backend_end_blocks
    
    def create_emperor_frontend(self,emperor_hash):
         #"emperor_domain": {"cluster_slug":"general","domains":[{"dev.debt-consolidation.com":{"ssl":true}}] },
        server_type_app_hash = {}
        
        acl_string = ''
        
        """
        Add the below if any domain with use ssl
        """
        use_acme = False
        for server_type,meta in emperor_hash.iteritems():
            for domain_hash in meta['domain']['domains']:
                domain = domain_hash.keys()[0]
                if domain_hash[domain].has_key('ssl') and domain_hash[domain]['ssl']==True:
                    use_acme = True      
        
        acl_string = ''
        if use_acme:
            acl_string = acl_string + 'acl url_acme_http01 path_beg /.well-known/acme-challenge/' + '\n'
            acl_string = acl_string + 'http-request use-service lua.acme-http01 if METH_GET url_acme_http01' + '\n'
        
        for server_type,meta in emperor_hash.iteritems():
            for domain_hash in meta['domain']['domains']:
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
        
        self.ha_front_end_blocks.append(t)
        return self.ha_front_end_blocks  
    
    def create_emperor_backend(self,emperor_hash):
        
        remote_port = 80
        proxy_port = 80
        mode = 'http'
        temp_ha = []

        for server_type,meta in emperor_hash.iteritems():
    
            base = meta['base']
            
            if meta['domain'].has_key('ssl') and meta['domain']['ssl']==True:
                    scheme_https = 'redirect scheme https if !{ ssl_fc }'
            else:
                scheme_https=''
                
            """

            
            "emperor_domain": {"cluster_slug":"api","ssl":true, "domains":[{"ass.iboot.io":{"ssl":false}}] },
            
            """

            
            if self.base_ip_hash.has_key(base):
                server_list = self.base_ip_hash[base] 
                temp = []
                if server_list:
                    for index,ip in enumerate(list(server_list)):
                        temp.append('server %s-%s %s:%s check cookie s%s' % (server_type,index+1,ip,remote_port,index+1))   
                    temp = '\n'.join(temp)
                else:
                    temp = None
                    

                
                if temp:
                    replace_values = { 'server_type':server_type,'mode':mode,'server_list':temp,'proxy_port':proxy_port,'remote_port':remote_port,'scheme_https':scheme_https}
                else:
                    replace_values = { 'server_type':server_type,'mode':mode,'server_list':'','proxy_port':proxy_port,'remote_port':remote_port,'scheme_https':scheme_https}
                    
                    

                    
                t = string.Template("""
                    
                backend ${server_type}_backend
                   option httpclose
                   option forwardfor
                   http-request set-header X-Forwarded-Port %[dst_port]
                   http-request add-header X-Forwarded-Proto https if { ssl_fc }
                   ${scheme_https}
                   cookie SERVERID insert indirect nocache
                   mode $mode
                   option ${mode}log
                   balance roundrobin
                   $server_list
                """)
                self.ha_backend_end_blocks.append(t.substitute(replace_values))
            else:
                #Is is the case where no servers.  Still have to add else haproxhy will bomb
                replace_values = { 'server_type':server_type,'mode':mode,'proxy_port':proxy_port,'remote_port':remote_port,'scheme_https':scheme_https}
                t = string.Template("""
                backend ${server_type}_backend
                   option httpclose
                   option forwardfor
                   http-request set-header X-Forwarded-Port %[dst_port]
                   http-request add-header X-Forwarded-Proto https if { ssl_fc }
                   ${scheme_https}
                   cookie SERVERID insert indirect nocache
                   mode $mode
                   option ${mode}log
                   balance roundrobin
                """)
                self.ha_backend_end_blocks.append(t.substitute(replace_values))
        
        
        
        return self.ha_backend_end_blocks
        
    def get_zk_base_ip_address(self,active_proxies):
        
        
        for server_type_cs in active_proxies:
            base = self.get_base_name_of_proxy_service(server_type_cs,use_services='')
            path = '/%s/' % base
            exists = zk.exists(path)
            print path
            if exists:
                address = zk.get_children(path)
                print path,address
                self.base_ip_hash[base]=list(address)
        
        return self.base_ip_hash
          
    def run(self):
        

        #SERVICE
        if self.server_type!='haproxy':
            active_proxies = self.create_proxy_service_list() 
            base_ip_hash = self.get_zk_base_ip_address(active_proxies)
            
            for server_type_cs in active_proxies: 
                meta = self.haproxy_server_params[server_type_cs]
                self.create_service_frontend(server_type_cs,meta)
                
            for server_type_cs in active_proxies: 
                meta = self.haproxy_server_params[server_type_cs]
                self.create_service_backend(server_type_cs,meta)
              

        if self.server_type=='haproxy':
            
            temp = self.haproxy_server_params.keys()
#             print temp
#             print self.server_type, self.cluster_slug
            
            
            server_type_cs = '%s-%s'% (self.server_type, self.cluster_slug)
            meta = self.haproxy_server_params[server_type_cs]
            
            
            
            if meta.has_key("emperor")==False or meta["emperor"]==False:
                emperor = False
            else:
                emperor = True

            if emperor==False:
                self.create_matchtype_frontend(meta)
                active_proxies = meta['include']
                base_ip_hash = self.get_zk_base_ip_address(active_proxies)
                self.create_matchtype_backend(meta)
                
            if emperor==True:
                
                emperor_hash = self.get_emperor_hash()
                active_proxies = emperor_hash.keys()
                base_ip_hash = self.get_zk_base_ip_address(active_proxies)

                self.create_emperor_frontend(emperor_hash)
                self.create_emperor_backend(emperor_hash)
                
        
        
        front_end_config = '\n' .join(self.ha_front_end_blocks)
        print front_end_config
        
        backend_config = '\n' .join(self.ha_backend_end_blocks)
        print backend_config 
        
        ha_proxy_config = """
            %s
            %s
            """ % (front_end_config,backend_config)

        haproxy_encode = hashlib.md5(ha_proxy_config).hexdigest()
        
        print haproxy_encode
        reload = False

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
                
  

haproxy_server_params = {
    "elasticsearch-openrx": {
        "host": "127.0.0.1",
        "mode": "tcp",
        "proxy_port": 9203,
        "remote_port": 9200,
        "include": ["aaa"]
    },
    "elasticsearch-dude": {
        "host": "127.0.0.1",
        "mode": "tcp",
        "proxy_port": 9203,
        "remote_port": 9200,
        "include": ["health"]
    },
    "mysql-health": {
        "host": "127.0.0.1",
        "mode": "tcp",
        "proxy_port": 9203,
        "remote_port": 9200,
        "include": []
    },
    "zookeeper": {
        "host": "127.0.0.1",
        "mode": "tcp",
        "proxy_port": 9203,
        "remote_port": 9200,
        "include": [],
        "frontend": {
            "exhibitor": {
                "host": "0.0.0.0",
                "remote_port": 8080,
                "proxy_port": 82,
                "mode": "http"
            }
        }
    },
    "kibana": {
        "host": "127.0.0.1",
        "mode": "tcp",
        "proxy_port": 9203,
        "remote_port": 9200,
        "exclude": ["health"]
    }


}



"""
* All haproxy nodes must have a cluster_slug
* Single - if include len =1 and emperor = false

"""

zk = None 
def wait_for_zk():
    zk = None
    while zk==None:
        zk = get_zk_conn()  
        time.sleep(1)
    return zk
   

while True:
    
    
    if zk:
    

        if os.path.isfile('/var/cluster_slug.txt'):
            cluster_slug = open("/var/cluster_slug.txt").readlines()[0].strip()
        else:
            cluster_slug = "nocluster"  
            
        
        temp = open('/var/zookeeper_node_name.json').readlines()[0]
        node,ip = temp.split(' ')
        server_type = node.split('-')[0]
        parms = getparms.get_parms(slug='forex')
        environment = parms['environment']
        location = parms['location']
        datacenter = parms['datacenter']
        slug = parms['slug']['slug']
    
        haproxy_server_params = parms[server_type]['haproxy']
    
        try:
            ha = haproxy(server_type,cluster_slug,haproxy_server_params,slug,datacenter,environment,location)
            ha.run()
        except:
            print 'HA LOOP'
            #http://stackoverflow.com/questions/8238360/how-to-save-traceback-sys-exc-info-values-in-a-variable
            print traceback.format_exc()
                             
        sys.stdout.flush()
        sys.stderr.flush()
        print '-'*20
        time.sleep(1)
        
    else:
        zk = wait_for_zk()
    
    

    
    
    
        
        
