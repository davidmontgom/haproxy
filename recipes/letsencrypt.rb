server_type = node.name.split('-')[0]
slug = node.name.split('-')[1] 
datacenter = node.name.split('-')[2]
environment = node.name.split('-')[3]
location = node.name.split('-')[4]
cluster_slug = File.read("/var/cluster_slug.txt")
cluster_slug = cluster_slug.gsub(/\n/, "") 

data_bag("meta_data_bag")
aws = data_bag_item("meta_data_bag", "aws")
domain = aws[node.chef_environment]["route53"]["domain"]

data_bag("server_data_bag")
haproxy_server = data_bag_item("server_data_bag", "haproxy")
subdomain = haproxy_server[datacenter][environment][location][cluster_slug]["haproxy_subdomain"]


if haproxy_server["haproxy"][cluster_slug].has_key?("ssl")
  ssl = haproxy_server["haproxy"][cluster_slug]["ssl"]
else
  ssl=false
end
  
full_domain = "#{subdomain}.#{domain}"


git "/opt/letsencrypt" do
  repository "https://github.com/letsencrypt/letsencrypt"
  action :sync
  user "root"
end

bash "letsencrypt_help" do
user "root"
code <<-EOH
  /opt/letsencrypt/letsencrypt-auto --help all
  touch /var/chef/cache/letsencrypt_help.lock
EOH
action :run
not_if {File.exists?("/var/chef/cache/letsencrypt_help.lock")}
end

if ssl==true
  #Install for match_type
  bash "letsencrypt_install" do
  user "root"
  code <<-EOH
    /opt/letsencrypt/letsencrypt-auto --email admin@example.com --agree-tos --renew-by-default \
                                      --standalone --standalone-supported-challenges http-01 certonly \
                                      -d #{full_domain}  
    touch /var/chef/cache/letsencrypt_install.lock
  EOH
  action :run
  not_if {File.exists?("/var/chef/cache/letsencrypt_install.lock")}
  end
end



=begin
http://blog.héry.com/article23/use-haproxy-with-let-s-encrypt
https://blog.brixit.nl/automating-letsencrypt-and-haproxy
1) Add all but comment out these lines 
#bind 0.0.0.0:443 ssl crt /etc/haproxy/ssl/
#reqadd X-Forwarded-Proto:\ https

2) move the certs

3) reload
cat dccomm-development.govspring.com/{fullchain.pem,privkey.pem} > /etc/haproxy/ssl/dccomm-development.govspring.com.pem

/opt/letsencrypt/letsencrypt-auto --email admin@example.com --agree-tos --renew-by-default --standalone --standalone-supported-challenges http-01 --http-01-port 9999 certonly  -d dashboard-cloud.feed-galaxy.com 

=end
=begin

      frontend frontend_front
           bind 0.0.0.0:80
           mode http
           option httplog
           reqadd X-Forwarded-Proto:\ http
           default_backend frontend_backend

       frontend frontend_front_https  
 
           bind 0.0.0.0:443 ssl crt /etc/haproxy/ssl/
           reqadd X-Forwarded-Proto:\ https
           acl letsencrypt-request path_beg -i /.well-known/acme-challenge/
           use_backend letsencrypt if letsencrypt-request
           default_backend frontend_backend
           
        backend frontend_backend
           option httpclose
           option forwardfor
           http-request set-header X-Forwarded-Port %[dst_port]
           http-request add-header X-Forwarded-Proto https if { ssl_fc }
           redirect scheme https if !{ ssl_fc }
           cookie SERVERID insert indirect nocache
           mode http
           option httplog
           balance roundrobin
           server frontend-1 192.34.60.133:80 check cookie s1

        backend letsencrypt
           mode http
           server letsencrypt 127.0.0.1:9999

=end


=begin
cold start
1) Prior to installing haproxy
* open port 80,443,9999

2) run the below commands 
/opt/letsencrypt/letsencrypt-auto --email admin@example.com --agree-tos --renew-by-default --standalone --standalone-supported-challenges http-01  certonly  -d monitor-feed-do-cloud-ny.feed-galaxy.com

3) install haprixyh

3) Move the certs to haroxy/ssl

4CTIVE THE renew cron bbbut use 9999

4) haproxy seerver will use the lowest index as masteeer  and sync with others

5) New servers will ssh into master and sync the certs

6) if master dies then 2 is master till new master is brought back up
=end














