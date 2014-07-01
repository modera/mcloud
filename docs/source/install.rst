
============================================
Installation
============================================

Instructions are given for Ubuntu linux, but except some details, like
package names and file-system paths, process is same on all operating systems.

Prerequisites
===============

Install docker and make sure it's working::

    sudo docker run -i -t ubuntu echo -e "OK";


Update package cache::

    sudo apt-get update

Install redis::

    sudo apt-get install redis-server

Required packages::

    sudo apt-get install python-dev python-virtualenv libffi-dev libssl-dev

Package installation
========================================

Install mfcloud packages::

    $ sudo mkdir /opt  # if you don't have it already
    $ sudo virtualenv /opt/mfcloud
    $ sudo /opt/mfcloud/bin/pip install mfcloud

Link mfcloud executables::

    $ sudo ln -s /opt/mfcloud/bin/mfcloud* /usr/local/bin/


Now you can run mfcloud-rpc-server.

mfcloud-server
================

Running mfcloud-server manualy
************************************

Running manualy is simplest way to run mfcloud-server.

Just open separate console and execute::

    $ sudo mfcloud-rpc-server

Sudo is required as commands also runs dns server on 53 port,
this action require super-use privileges.


Running mfcloud-server with supervisor
****************************************

Install supervisor::

    $ apt-get install supervisor

Create file /etc/supervisor/conf.d/mfcloud.conf with following contents::

    [program:mfcloud]
    command=/opt/mfcloud/bin/mfcloud-rpc-server

Start service::

    $ sudo supervisorctl start mfcloud

Make sure it's running::

    $ ps ax | grep mfcloud

    3920 ?        Ssl    0:00 /opt/mfcloud/bin/python /opt/mfcloud/bin/mfcloud-rpc-server
    3937 pts/5    S+     0:00 grep --color=auto mfcloud



Running mfcloud-server with upstart
************************************

Create file /etc/init/mfcloud.conf with follwing contents::

    exec /opt/mfcloud/bin/mfcloud-rpc-server >> /var/log/mfcloud.log 2>&1

Start mfcloud service::

    $ sudo service mfcloud start

Make sure it's running::

    $ ps ax | grep mfcloud

    3920 ?        Ssl    0:00 /opt/mfcloud/bin/python /opt/mfcloud/bin/mfcloud-rpc-server
    3937 pts/5    S+     0:00 grep --color=auto mfcloud


Configure system to use mfcloud-dns
======================================

On linux just add "172.17.42.1" to /etc/resolv.conf
But this settings will be overridden on next reboot.
To add new dns permanently you may add this record to /etc/network/interfaces.

Example of /etc/network/interfaces::

    auto lo
    iface lo inet loopback

    dns-nameservers 172.17.42.1 8.8.8.8

https://help.ubuntu.com/12.04/serverguide/network-configuration.html#name-resolution


For mac you can use this link, to get an idea how to add another dns server: http://macs.about.com/od/networking/qt/configure-your-macs-dns.htm



Checking installation
===========================================

Ping dns to make sure it's there::

    $ ping _dns.mfcloud.lh

    PING _dns.mfcloud.lh (127.0.0.1) 56(84) bytes of data.
    64 bytes from localhost (127.0.0.1): icmp_req=1 ttl=64 time=0.020 ms
    64 bytes from localhost (127.0.0.1): icmp_req=2 ttl=64 time=0.035 ms
    ^C
    --- dns.mfcloud.lh ping statistics ---
    2 packets transmitted, 2 received, 0% packet loss, time 999ms
    rtt min/avg/max/mdev = 0.020/0.027/0.035/0.009 ms

Or use dig utility::

    $ dig _dns.mfcloud.lh

    ; <<>> DiG 9.9.2-P1 <<>> _dns.mfcloud.lh
    ;; global options: +cmd
    ;; Got answer:
    ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 47330
    ;; flags: qr ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0

    ;; QUESTION SECTION:
    ;_dns.mfcloud.lh.		IN	A

    ;; ANSWER SECTION:
    _dns.mfcloud.lh.	10	IN	A	127.0.0.1

    ;; Query time: 0 msec
    ;; SERVER: 172.17.42.1#53(172.17.42.1)
    ;; WHEN: Sat Jun 28 16:21:54 2014
    ;; MSG SIZE  rcvd: 49


If dns is working, then _dns.mfcloud.lh is resolved to 127.0.0.1

Check that API is up::

    $ mfcloud list

    +------------------+-------------------------+---------+-----------------------------------------------------+
    | Application name |           Web           |  status |                       services                      |
    +------------------+-------------------------+---------+-----------------------------------------------------+


Updating mflcoud
============================================

Update is easy::

    $ sudo /opt/mfcloud/bin/pip install -U mfcloud

And restart service::

    $ sudo service mfcloud restart

Uninstalling mflcoud
============================================

- Remove upstart/supervisor script
- If, you used mfcloud with supervisor, you may need to uninstall supervisor as well
- Remove mfcloud commands: sudo rm /usr/local/bin/mfcloud*
- Remove mfcloud home: sudo rm -rf /opt/mfcloud
- Remove mflcoud-dns


