


git "/var/haproxy-acme-validation-plugin" do
  repository "https://github.com/janeczku/haproxy-acme-validation-plugin.git"
  action :sync
  user "root"
end

=begin
bash "letsencrypt_help" do
user "root"
code <<-EOH
  git clone https://github.com/janeczku/haproxy-acme-validation-plugin.git
  
  touch /var/chef/cache/letsencrypt_help.lock
EOH
action :run
not_if {File.exists?("/var/chef/cache/letsencrypt_help.lock")}
=end