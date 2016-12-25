





bash 'install_certbot' do
  code <<-EOH
    wget https://dl.eff.org/certbot-auto
	chmod a+x certbot-auto
	echo "y" | ./certbot-auto
	touch /var/chef/cache/certbot.lock
  EOH
  action :run
  not_if {File.exists?("/var/chef/cache/certbot.lock")}
end

