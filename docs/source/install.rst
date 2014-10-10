
============================================
Installation
============================================

Instructions are given for Ubuntu linux, but except some details, like
package names and file-system paths, process is same on all operating systems.

Preparing operating system
============================

To run mcloud you need linux operating system with docker installed.
boot2docker is not supported, but it's easy to install mcloud inside virtualbox
same way as boot2docker does.

There is two options:

- you are working on linux machine: install mcloud right on your machine
- you are working on mac/windows/other OS: install mcloud inside virtualbox and map project directories, through nfs/smb

Follow configuration manual of your OS:

.. toctree::
  :maxdepth: 3

  install/macos
  install/ubuntu

At the end you will get same ubuntu machine and you can easily follow further steps of this manual.
If you are working on other linux distributions, adapt commands and package names accordingly.


Mcloud installation
==========================

Install docker and make sure it's working::

    sudo docker run -i -t ubuntu echo -e "OK";


Update package cache::

    sudo apt-get update

Install redis::

    sudo apt-get install redis-server

Required packages::

    sudo apt-get install python-dev python-virtualenv libffi-dev libssl-dev libncurses5-dev libreadline-dev

.. note::

    If you want to use docker command without sudo as we do in this document, you should
    add you user to docker group. For, example:

    $ sudo usermod -G docker -a `whoami`

    Then usually it's enough to login/logout into your terminal,
    but in some cases system restart maybe needed.

    To test, type (without sudo):

    $ docker ps

    If, you see no errors, then it works.

    *NB!* This is DANGEROUS settings in production. Adding user to docker group
    basically means you give root priveleges to this user.



Package installation
========================================

Add modera ubuntu repository::

    wget -O - https://ubuntu.dev.modera.org/moderaci.gpg.key|apt-key add -
    echo "deb http://ubuntu.dev.modera.org/debian trusty main" > /etc/apt/sources.list.d/modera.list
    apt-get update

Install mcloud

    apt-get install mcloud


Install mcloud packages::

    $ sudo mkdir /opt  # if you don't have it already
    $ sudo virtualenv /opt/mcloud
    $ sudo /opt/mcloud/bin/pip install mcloud

Link mcloud executables::

    $ sudo ln -s /opt/mcloud/bin/mcloud* /usr/local/bin/


Now you can run mcloud-rpc-server.

mcloud-server
================

Running mcloud-server manualy
************************************

Running manualy is simplest way to run mcloud-server.

Just open separate console and execute::

    $ sudo mcloud-rpc-server

Sudo is required as commands also runs dns server on 53 port,
this action require super-use privileges.

Install dnsmasq server
***************************************

.. note::

    If you are updating from previous version of mcloud, stop mcloud server before installing dnsmasq
    (sudo service mcloud stop)

dnsmasq acts as dns proxy for local machine, we will configure it to proxify all request
to outer dns servers, except mcloud.lh subdomain.

Install dnamasq:

    sudo apt-get install dnsmasq

Replace content of /etc/dnsmasq.conf file with following 3 lines::

    interface=lo
    interface=docker0
    server=/mcloud.lh/172.17.42.1#7053

Replace '172.17.42.1' with your docker interface ip. You can get it using ifconfig command::

    $ ifconfig docker0

Start dnsmasq server::

    $ sudo service dnsmasq start


Running mcloud-server with supervisor
****************************************

Install supervisor::

    $ apt-get install supervisor

Create file /etc/supervisor/conf.d/mcloud.conf with following contents::

    [program:mcloud]
    command=/opt/mcloud/bin/mcloud-rpc-server

Start service::

    $ sudo supervisorctl start mcloud

Make sure it's running::

    $ ps ax | grep mcloud

    3920 ?        Ssl    0:00 /opt/mcloud/bin/python /opt/mcloud/bin/mcloud-rpc-server
    3937 pts/5    S+     0:00 grep --color=auto mcloud



Running mcloud-server with upstart (recommended)
***************************************************

Create file /etc/init/mcloud.conf with follwing contents::

    description "Mcloud server"
    author "Modera"
    start on filesystem and started docker
    stop on runlevel [!2345]
    respawn
    script
      /opt/mcloud/bin/mcloud-rpc-server >> /var/log/mcloud.log 2>&1
    end script

Start mcloud service::

    $ sudo service mcloud start

Make sure it's running::

    $ ps ax | grep mcloud

    3920 ?        Ssl    0:00 /opt/mcloud/bin/python /opt/mcloud/bin/mcloud-rpc-server
    3937 pts/5    S+     0:00 grep --color=auto mcloud


Installing haproxy
==========================

Haproxy is only needed when you install mcloud on remote sever or
if you run mcloud in virtual machine, and want to access applications from
your host machine by domain names like **.mflcoud.lh

Install haproxy::

    $ sudo apt-get install haproxy

Then edit /etc/default/haproxy and set ENABLED=1

Then start haproxy service::

    $ sudo service haproxy start

Also you need to add *--haproxy* option to the mcloud-rpc-server command.
To do this, edit /etc/init/mcloud.conf and add this option to the end::

    exec /opt/mcloud/bin/mcloud-rpc-server --haproxy  >> /var/log/mcloud.log 2>&1

And finally restart mcloud::

    $ service mcloud restart

.. note::

    To use **.mcloud.lh with mcloud inside virtual machine, you also need to configure
    your local machine to use the virtual machine as dns-server, ex.:
    http://stackoverflow.com/questions/138162/wildcards-in-a-hosts-file


Checking installation
===========================================

Ping dns to make sure it's there::

    $ ping _dns.mcloud.lh

    PING _dns.mcloud.lh (127.0.0.1) 56(84) bytes of data.
    64 bytes from localhost (127.0.0.1): icmp_req=1 ttl=64 time=0.020 ms
    64 bytes from localhost (127.0.0.1): icmp_req=2 ttl=64 time=0.035 ms
    ^C
    --- dns.mcloud.lh ping statistics ---
    2 packets transmitted, 2 received, 0% packet loss, time 999ms
    rtt min/avg/max/mdev = 0.020/0.027/0.035/0.009 ms

Or use dig utility::

    $ dig _dns.mcloud.lh

    ; <<>> DiG 9.9.2-P1 <<>> _dns.mcloud.lh
    ;; global options: +cmd
    ;; Got answer:
    ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 47330
    ;; flags: qr ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0

    ;; QUESTION SECTION:
    ;_dns.mcloud.lh.		IN	A

    ;; ANSWER SECTION:
    _dns.mcloud.lh.	10	IN	A	127.0.0.1

    ;; Query time: 0 msec
    ;; SERVER: 172.17.42.1#53(172.17.42.1)
    ;; WHEN: Sat Jun 28 16:21:54 2014
    ;; MSG SIZE  rcvd: 49


If dns is working, then _dns.mcloud.lh is resolved to 127.0.0.1

Check that API is up::

    $ mcloud list

    +------------------+-------------------------+---------+-----------------------------------------------------+
    | Application name |           Web           |  status |                       services                      |
    +------------------+-------------------------+---------+-----------------------------------------------------+


Updating mflcoud
============================================

Update is easy::

    $ sudo /opt/mcloud/bin/pip install -U mcloud

And restart service::

    $ sudo service mcloud restart

Uninstalling mflcoud
============================================

- Remove upstart/supervisor script
- If, you used mcloud with supervisor, you may need to uninstall supervisor as well
- Remove mcloud commands: sudo rm /usr/local/bin/mcloud*
- Remove mcloud home: sudo rm -rf /opt/mcloud
- Remove mflcoud-dns
