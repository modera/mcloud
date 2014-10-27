
==========================================
Solving usual problems
==========================================

Can't connect to xxx - connection refused
============================================

Read "Container start fine-tuning"

Can't resolve xxx
========================

Sympthoms:

- mcloud list reports, that application is running, but borwser says "cant resolve server name XXX"
- container logs contain messages like, can't connect to XXX

Where XXX is som domain name like redis-flask.mcloud.lh, or "mysql", "redis" for services

Possible cause:

- docker daemon wen't crayzy and crashed network on containers (docker inspect xxx shows no ip address assigned)
- dnsmasq is not started/ not configured properly

Try:

- sudo service docker restart
- sudo service dnsmasq restart
- sudo service mcloud restart

Finding exact cause:

- dig @dockerip -p 7053 XXX  # if fails, restart mcloud - mcloud fail
- check dnsmasq is configured to forward mcloud.lh domains to docker ip port 7053
- check dnsmasq is listening on dockerip 53 port
- dig @dockerip XXX  # if fails, restart dnsmassq - dnasmasq fail
- check /etc/resolv.conf contains "nameserver 127.0.0.1" on first line
- check /etc/dnsmasq.conf contains "server=/mcloud.lh/172.17.42.1#7053" (add it with ip of docker0 interface, if missing)


