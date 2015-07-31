
============================================
Installing environment
============================================

Docker
--------------------

Docker is most important part of our setup. It runs everything, including mcloud.

You can find instructions on how install docker on different operating systems on
docker website https://docs.docker.com/

Verify docker is installed and at least 1.7 version::

    $ docker version

    Client version: 1.7.1
    Client API version: 1.19
    Go version (client): go1.4.2
    Git commit (client): 786b29d
    OS/Arch (client): linux/amd64
    Server version: 1.7.1
    Server API version: 1.19
    Go version (server): go1.4.2
    Git commit (server): 786b29d
    OS/Arch (server): linux/amd64

.. note::

    Recommended way to install docker on MacOS is `docker-machine <https://docs.docker.com/machine/>`_. And don't forget to use
    `nfs in case of virtualbox <https://github.com/adlogix/docker-machine-nfs>`_.


Mcloud Server
-----------------

Mcloud server is orchestration tool that will setup docker container to run our application.

Installation is easy. Just start it as docker container.

MacOS::

    docker run -d --restart always -v /Users:/Users -v /var/run/docker.sock:/var/run/docker.sock --name mcloud mcloud/mcloud

Linux::

    docker run -d --restart always -v /home:/home -v /var/run/docker.sock:/var/run/docker.sock --name mcloud mcloud/mcloud

Haproxy
------------------

Haproxy is needed because we plan to host lot of applications on our machine, so they should share port :80.

Mcloud have speciall plugins that install haproxy as docker-container automatically::

    $ docker exec -it mcloud mcloud-plugins install mcloud-plugin-haproxy
    $ docker restart mcloud

Check logs and wait until mcloud start (it takes some time to download haproxy image)::

    $ docker logs -f mcloud

Make sure haproxy container is started::

    $ docker ps

You should see mcloud_haproxy container running.

Dnsmasq
-----------------

The only reason why dnsmasq is needed is to point all the domains *.mcloud.lh to machine where docker is installed.
On linux it is 127.0.0.1, on windows and mac it's virtual machines's ip.

.. note::

    Dnsmasq step is pure optional, but then you need manually add records to /etc/hosts file.

Install dnsmasq. Ex. using this guide for mac os: http://passingcuriosity.com/2013/dnsmasq-dev-osx/


update config file with following line::

    address=/mcloud.lh/127.0.0.1

Don't forget to replace 127.0.0.1 with virtual machine ip, if not on linux.


Mcloud Client
-----------------

Mcloud Client is console utility, that we will use to control mcloud.

Mcloud client can be executed in separate container and linked to Mcloud Server container::

    docker run -i -t --volumes-from mcloud --link mcloud --rm -w `pwd` mcloud/mcloud mcloud

.. note::

    docker automatically destroy this container, when mcloud client execution ends.

If you don't want to type this command every time, add it as alias to your .bash_profile or .bashrc::

    alias mcloud='docker run -i -t --volumes-from mcloud --link mcloud --rm -w `pwd` mcloud/mcloud mcloud'

Then you can just type "mcloud".


Verify installation
---------------------

And quick-check that mcloud is working::

    $  mcloud -V

    mcloud 0.11.8

    $ mcloud list

    +------------------+------------+--------+-------+--------+-----+------+
    | Application name | deployment | status | cpu % | memory | Web | Path |
    +------------------+------------+--------+-------+--------+-----+------+



What we have now
--------------------


What we need to achieve is following picture:

.. uml::

    cloud "Web browser" as WebBrowser {

    }

    node "Developer machine" as DeveloperMachine {

        () "127.0.0.1:80" as port_80
        () "127.0.0.1:53" as port_53

        package Docker {

            [Mcloud Server] as server

            [Mcloud Client] as client

            client .right.> server : Use WebSocketAPI

            [Haproxy] << Load Balancer >>

            [nginx.myapp]

            Haproxy -left-> nginx.myapp

            Haproxy - port_80

            server ..> Haproxy
            server ..> nginx.myapp : configure \n& controll \ncontainers
        }

        [Dnsmasq]

        Dnsmasq -left- port_53
    }
    WebBrowser ..left..> port_53
    WebBrowser ..left..> port_80


What will happen when myapp.mcloud.lh is opened:

.. uml::

    group Dns request
        WebBrowser -> Dnsmasq : who is myapp.mcloud.lh ?
        activate Dnsmasq
        Dnsmasq -> WebBrowser : all *.mcloud.lh domains belong to 127.0.0.1
        deactivate Dnsmasq
    end

    group Http request
        WebBrowser -> Haproxy : GET /path/file.html HTTP/1.1 \nHost: myapp.mcloud.lh:80
        activate Haproxy #FFBBBB

        Haproxy -> Haproxy : who is myapp.mcloud.lh?
        Haproxy -> Haproxy : it is nginx.myapp.mcloud.lh port 80

        Haproxy -> nginx.myapp : GET / HTTP/1.1 \nHost: myapp.mcloud.lh:80
        activate nginx.myapp #DarkSalmon

        nginx.myapp -> Haproxy : <htm>...</html>
        deactivate nginx.myapp

        Haproxy -> WebBrowser : <htm>...</html>
        deactivate Haproxy

    end


