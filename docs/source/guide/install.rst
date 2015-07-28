
============================================
Installation
============================================

Mcloud has server and client parts:

.. uml::

    [Mcloud client] as cli
    [Mcloud server] as srv

    cli .right.> srv : WebsocketAPI


    srv .down.> [Docker1] : RemoteAPI
    srv .down.> [Docker2] : RemoteAPI
    srv .down.> [Docker3] : RemoteAPI


Prerequisites
--------------------

Mcloud requires docker. You can find instructions on how install docker on different operating systems on
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

Easiest and recommended way to install ModeraCloud is start it inside docker container.

First we need to start mcloud server.


MacOS::

    docker run -d --restart always -v /Users:/Users -v /var/run/docker.sock:/var/run/docker.sock --name mcloud mcloud/mcloud

Linux::

    docker run -d --restart always -v /home:/home -v /var/run/docker.sock:/var/run/docker.sock --name mcloud mcloud/mcloud

.. note::

    Mcloud server update can be done this way::

        $ docker exec -it mcloud mcloud-plugins install -U mcloud


Mcloud Client
-----------------

ModeraCloud client can be run from docker as well using this command::

    docker run -i -t --volumes-from mcloud --link mcloud --rm -w `pwd` mcloud/mcloud mcloud


If you don't want to type this command every time, add it as alias to your .bash_profile or .bashrc::

    alias mcloud='docker run -i -t --volumes-from mcloud --link mcloud --rm -w `pwd` mcloud/mcloud mcloud'


Verify installation
---------------------

And quick-check that mcloud is working::

    $ mcloud list

    +------------------+------------+--------+-------+--------+-----+------+
    | Application name | deployment | status | cpu % | memory | Web | Path |
    +------------------+------------+--------+-------+--------+-----+------+
