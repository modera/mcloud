
============================================
Installation
============================================

Instructions are given for Ubuntu linux, but except some details, like
package names and file-system paths, process is same on all operating systems.

Preparing operating system
============================

To run mfcloud you need linux operating system with docker installed.
boot2docker is not supported, but it's easy to install mfcloud inside virtualbox
same way as boot2docker does.

There is two options:

- you are working on linux machine: install mfcloud right on your machine
- you are working on mac/windows/other OS: install mfcloud inside virtualbox and map project directories, through nfs/smb

Follow configuration manual of your OS:

.. toctree::
  :maxdepth: 3

  install/macos
  install/ubuntu

At the end you will get same ubuntu machine and you can easily follow further steps of this manual.
If you are working on other linux distributions, adapt commands and package names accordingly.


Mfcloud installation
==========================

Install docker and make sure it's working::

    sudo docker run -i -t ubuntu echo -e "OK";


Update package cache::

    sudo apt-get update

Install redis::

    sudo apt-get install redis-server

Required packages::

    sudo apt-get install python-dev python-virtualenv libffi-dev libssl-dev

.. note::

    If you want to use docker command without sudo as we do in this document, you should
    add you user to docker group. For, example:

    $ sudo usermod -G docker -a `whoami`

    Then usually it's enough to login/logout into your terminal,
    but in some cases system restart maybe needed.

    To test, type (without sudo):

    $ docker ps

    If, you see no errors, then it works.s



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

    start on startup
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


Installing haproxy
==========================

Haproxy is only needed when you install mfcloud on remote sever or
if you run mfcloud in virtual machine, and want to access applications from
your host machine by domain names like **.mflcoud.lh

Install haproxy::

    $ sudo apt-get install haproxy

Then edit /etc/default/haproxy and set ENABLED=1

Then start haproxy service::

    $ sudo service haproxy start

Also you need to add *--haproxy* option to the mfcloud-rpc-server command.
To do this, edit /etc/init/mfcloud.conf and add this option to the end::

    exec /opt/mfcloud/bin/mfcloud-rpc-server --haproxy  >> /var/log/mfcloud.log 2>&1

And finally restart mfcloud::

    $ service mfcloud restart

.. note::

    To use **.mfcloud.lh with mfcloud inside virtual machine, you also need to configure
    your local machine to use the virtual machine as dns-server, ex.:
    http://stackoverflow.com/questions/138162/wildcards-in-a-hosts-file


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


