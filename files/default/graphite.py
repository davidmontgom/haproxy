import requests
from requests.auth import HTTPBasicAuth
import csv

server_type = 'widget'

"""
https://cbonte.github.io/haproxy-dconv/configuration-1.5.html#9.1
ab -n 2000 -c 10 "http://widget-server.feed-galaxy.com/hash?placement_id=0000&publisher_id=0000"
"""
r = requests.get('http://159.203.246.201:9000/haproxy_stats;csv', auth=HTTPBasicAuth('admin', 'Test101'))
data = r.text

reader = csv.DictReader(data.splitlines(), delimiter=',')
for row in reader:
    print row['svname'],row['# pxname'], row
    
    
    
    
    
    
    
    
your processes number limit is 15845
your memory page size is 4096 bytes
detected max file descriptor number: 100000
- async cores set to 40 - fd table size: 100000
lock engine: pthread robust mutexes
thunder lock: disabled (you can enable it with --thunder-lock)
Listen queue size is greater than the system max net.core.somaxconn (128).
your processes number limit is 15845
your memory page size is 4096 bytes
detected max file descriptor number: 100000
- async cores set to 40 - fd table size: 100000
lock engine: pthread robust mutexes
thunder lock: disabled (you can enable it with --thunder-lock)
Listen queue size is greater than the system max net.core.somaxconn (128).
your processes number limit is 15845
your memory page size is 4096 bytes
detected max file descriptor number: 100000
- async cores set to 40 - fd table size: 100000
lock engine: pthread robust mutexes
thunder lock: disabled (you can enable it with --thunder-lock)
Listen queue size is greater than the system max net.core.somaxconn (128).
your processes number limit is 15845
your memory page size is 4096 bytes
detected max file descriptor number: 100000
- async cores set to 40 - fd table size: 100000
lock engine: pthread robust mutexes
thunder lock: disabled (you can enable it with --thunder-lock)
Listen queue size is greater than the system max net.core.somaxconn (128).
your processes number limit is 15845
your memory page size is 4096 bytes
detected max file descriptor number: 100000
- async cores set to 40 - fd table size: 100000
lock engine: pthread robust mutexes
