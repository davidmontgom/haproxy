server_type = node.name.split('-')[0]
slug = node.name.split('-')[1] 
datacenter = node.name.split('-')[2]
environment = node.name.split('-')[3]
location = node.name.split('-')[4]
cluster_slug = File.read("/var/cluster_slug.txt")
cluster_slug = cluster_slug.gsub(/\n/, "") 

data_bag("meta_data_bag")
git = data_bag_item("meta_data_bag", "git")
git_account = git["git_account"]
git_host = git["git_host"]

if node.chef_environment == "production"
    branch_name = "master"
    bootops_branch_name = "master"
else
    branch_name = node.chef_environment
    bootops_branch_name = "development"
end


git "/var/haproxy-acme-validation-plugin" do
  repository "https://github.com/janeczku/haproxy-acme-validation-plugin.git"
  action :sync
  user "root"
end

=begin
cron 'cert_renew' do
  minute '5'
  hour '8'
  day '*'
  month '*'
  weekday '6'
  command '/bin/sh /var/haproxy-acme-validation-plugin/cert-renewal-haproxy.sh'
end
#5 8 * * 6 /usr/bin/cert-renewal-haproxy.sh
=end


=begin
if File.exists?("/var/haproxy-acme-validation-plugin/acme-http01-webroot.lua")
    use_acme = 'lua-load /var/haproxy-acme-validation-plugin/acme-http01-webroot.lua'
else
    use_acme = ' '
end 
=end

 
=begin
ha_services = node["haproxy"]
ha_services_json=ha_services.to_json

file "/var/ha_services.json" do
  owner 'root'
  group 'root'
  mode '0666'
  content "#{ha_services_json}"
end
=end

git "/var/bootops" do
    repository "git@bitbucket.org:davidmontgom/bootops.git"
    revision bootops_branch_name
    action :sync
    user "root"
end
bash "install bootops" do
  user "root"
  code <<-EOH
    cd /var/bootops
    /usr/bin/python setup.py install
  EOH
  action :run
end


bash "haproxy_template" do
  user "root"
  code <<-EOH
   add-apt-repository ppa:vbernat/haproxy-1.6
   apt-get update
  EOH
  action :run
  not_if {File.exists?("/etc/haproxy/haproxy.cfg")}
end

package "haproxy" do
  action :install
end

service "haproxy" do
  supports :restart => true, :start => true, :stop => true
  action [ :enable, :start]
end


directory "/etc/haproxy/conf.d" do
  mode "0600"
  owner 'root'
  group 'root'
  action :create
end

directory "/etc/haproxy/ssl" do
  mode "0600"
  owner 'root'
  group 'root'
  action :create
end

template "/etc/default/haproxy" do
    path "/etc/default/haproxy"
    source "haproxy.erb"
    owner "root"
    group "root"
    mode "0700"
    notifies :restart, resources(:service => "haproxy")
end

template "/etc/haproxy/haproxy.cfg" do
    path "/etc/haproxy/haproxy.cfg"
    source "haproxy.cfg.erb"
    owner "root"
    group "root"
    mode "0700"
    notifies :restart, resources(:service => "haproxy")
    not_if {File.exists?("/var/chef/cache/haproxy_template.lock")}
end

template "/etc/haproxy/haproxy.cfg.orig" do
    path "/etc/haproxy/haproxy.cfg.orig"
    source "haproxy.cfg.erb"
    owner "root"
    group "root"
    mode "0700"
    #variables lazy {{:use_acme => use_acme}}  
end


 

bash "haproxy_template" do
  user "root"
  code <<-EOH
   touch /var/chef/cache/haproxy_template.lock
  EOH
  action :run
end

execute "restart_haproxy_health" do
  command "sudo supervisorctl restart haproxy_zookeeper_server:"
  action :nothing
end

cookbook_file "/var/haproxy_zookeeper.py" do
  source "haproxy_zookeeper.py"
  mode "700"
  notifies :run, "execute[restart_haproxy_health]"
  #notifies :restart, resources(:service => "supervisord")
end


template "/etc/supervisor/conf.d/supervisord.haproxy.zookeeper.include.conf" do
  path "/etc/supervisor/conf.d/supervisord.haproxy.zookeeper.include.conf"
  source "supervisord.haproxy.zookeeper.include.conf.erb"
  owner "root"
  group "root"
  mode "700"
  notifies :restart, resources(:service => "supervisord"), :immediately 
end
service "supervisord"









