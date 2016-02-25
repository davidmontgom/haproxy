
package "python-dev" do
  action :install
end

package "libffi-dev" do
  action :install
end

package "libssl-dev" do
  action :install
end

#sudo apt-get install letsencrypt
#pip install 'requests[security]'

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

=begin
http://blog.héry.com/article23/use-haproxy-with-let-s-encrypt
https://blog.brixit.nl/automating-letsencrypt-and-haproxy
1) Add all but comment out these lines 
#bind 0.0.0.0:443 ssl crt /etc/haproxy/ssl/
#reqadd X-Forwarded-Proto:\ https

2) move the certs

3) reload
cat dashboard-cloud.feed-galaxy.com/{fullchain.pem,privkey.pem} > /etc/haproxy/ssl/dashboard-cloud.feed-galaxy.com.pem

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