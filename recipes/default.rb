datacenter = node.name.split('-')[0]
server_type = node.name.split('-')[1]
location = node.name.split('-')[2]
  
#data_bag("my_data_bag")
#ha = data_bag_item("my_data_bag", "haproxy")
#ha_services = ha[node.chef_environment]
ha_services = node["haproxy"]
ha_services_json=ha_services.to_json

file "/var/ha_services.json" do
  owner 'root'
  group 'root'
  mode '0666'
  content "#{ha_services_json}"
end



bash "haproxy_template" do
  user "root"
  code <<-EOH
   add-apt-repository ppa:vbernat/haproxy-1.5
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

template "/etc/default/haproxy" do
    path "/etc/default/haproxy"
    source "haproxy.erb"
    owner "root"
    group "root"
    mode "0755"
    notifies :restart, resources(:service => "haproxy")
end

template "/etc/haproxy/haproxy.cfg" do
    path "/etc/haproxy/haproxy.cfg"
    source "haproxy.cfg.erb"
    owner "root"
    group "root"
    mode "0755"
    notifies :restart, resources(:service => "haproxy")
    not_if {File.exists?("/var/chef/cache/haproxy_template.lock")}
end

template "/etc/haproxy/haproxy.cfg.orig" do
    path "/etc/haproxy/haproxy.cfg.orig"
    source "haproxy.cfg.erb"
    owner "root"
    group "root"
    mode "0755"
end
 

bash "haproxy_template" do
  user "root"
  code <<-EOH
   touch /var/chef/cache/haproxy_template.lock
  EOH
  action :run
end


cookbook_file "/var/haproxy_zookeeper.py" do
  source "haproxy_zookeeper.py"
  mode 00744
end


template "/etc/supervisor/conf.d/supervisord.haproxy.zookeeper.include.conf" do
  path "/etc/supervisor/conf.d/supervisord.haproxy.zookeeper.include.conf"
  source "supervisord.haproxy.zookeeper.include.conf.erb"
  owner "root"
  group "root"
  mode "0755"
  notifies :restart, resources(:service => "supervisord"), :immediately 
end
service "supervisord"









