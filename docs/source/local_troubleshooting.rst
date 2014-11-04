
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


Errors during build from Dockerfile
=======================================

If you have something similar, when container image is building from Dockerfile::

    W: Failed to fetch http://archive.ubuntu.com/ubuntu/dists/trusty/InRelease

    W: Failed to fetch http://archive.ubuntu.com/ubuntu/dists/trusty-updates/InRelease

    W: Failed to fetch http://archive.ubuntu.com/ubuntu/dists/trusty-security/InRelease

    W: Failed to fetch http://archive.ubuntu.com/ubuntu/dists/trusty-proposed/InRelease

    W: Failed to fetch http://archive.ubuntu.com/ubuntu/dists/trusty/Release.gpg  Could not resolve 'archive.ubuntu.com'

    W: Failed to fetch http://archive.ubuntu.com/ubuntu/dists/trusty-updates/Release.gpg  Could not resolve 'archive.ubuntu.com'

    W: Failed to fetch http://archive.ubuntu.com/ubuntu/dists/trusty-security/Release.gpg  Could not resolve 'archive.ubuntu.com'

    W: Failed to fetch http://archive.ubuntu.com/ubuntu/dists/trusty-proposed/Release.gpg  Could not resolve 'archive.ubuntu.com'

    W: Some index files failed to download. They have been ignored, or old ones used instead.

Then it may be docker's problem.

Just restart docker service::

    sudo service docker.io restart
