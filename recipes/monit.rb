service "monit"
template "/etc/monit/conf.d/haproxy.conf" do
  path "/etc/monit/conf.d/haproxy.conf"
  source "monit.haproxy.conf.erb"
  owner "root"
  group "root"
  mode "0755"
  notifies :restart, resources(:service => "monit")
end