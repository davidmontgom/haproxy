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

full_domain = "#{subdomain}.#{domain}"

if haproxy_server["haproxy"][cluster_slug].has_key?("ssl")
  ssl = haproxy_server["haproxy"][cluster_slug]["ssl"]
else
  ssl=false
end

if ssl==true
  bash "letsencrypt_install_ssl" do
  user "root"
  code <<-EOH
    cat #{full_domain}/{fullchain.pem,privkey.pem} > /etc/haproxy/ssl/#{full_domain}.pem
    service haproxy reload
    touch /var/chef/cache/letsencrypt_install_ssl.lock
  EOH
  action :run
  not_if {File.exists?("/var/chef/cache/letsencrypt_install_ssl.lock")}
  end
end