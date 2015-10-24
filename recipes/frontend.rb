

bash "ufw_enable_80" do
  user "root"
  cwd "#{Chef::Config[:file_cache_path]}"
  code <<-EOH
    sudo ufw allow 80/tcp
    touch #{Chef::Config[:file_cache_path]}/ufw_enable_80
  EOH
  action :run
  not_if {File.exists?("#{Chef::Config[:file_cache_path]}/ufw_enable_80")}
end

