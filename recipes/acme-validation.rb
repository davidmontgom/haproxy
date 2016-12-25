


git "/var/haproxy-acme-validation-plugin" do
  repository "https://github.com/janeczku/haproxy-acme-validation-plugin.git"
  action :sync
  user "root"
end

template "/var/cert-renewal-haproxy.sh" do
  path "/var/cert-renewal-haproxy.sh"
  source "cert-renewal-haproxy.sh.erb"
  owner "root"
  group "root"
  mode "0755"
end




=begin
cron 'cert_renew' do
  hour '5'
  minute '0'
  command '/bin/sh /var/cert-renewal-haproxy.sh'
end
=end
