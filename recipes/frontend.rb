server_type = node.name.split('-')[0]
slug = node.name.split('-')[1] 
datacenter = node.name.split('-')[2]
environment = node.name.split('-')[3]
location = node.name.split('-')[4]
cluster_slug = File.read("/var/cluster_slug.txt")
cluster_slug = cluster_slug.gsub(/\n/, "") 


data_bag("server_data_bag")
haproxy_server = data_bag_item("server_data_bag", "haproxy")

public_ports = haproxy_server_server[datacenter][environment][location][cluster_slug]['public_ports']


public_ports.each do |port|
  
  bash "open_public_ports" do
      user "root"
      code <<-EOH
        
        /sbin/iptables -I INPUT -i eth0 -p tcp --dport #{port} -m state --state NEW,ESTABLISHED -j ACCEPT
        /sbin/iptables -I INPUT -i eth0 -p tcp --sport #{port} -m state --state ESTABLISHED -j ACCEPT
        /etc/init.d/iptables-persistent save
        touch /var/chef/cache/iptables_#{port}.lock
      EOH
      action :run
      not_if {File.exists?("/var/chef/cache/iptables_#{port}.lock")}
  end

end


