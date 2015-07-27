
Haproxy
==============

Description
---------------

Installs new docker container with haproxy inside, listen for container updates
and reconfigure haproxy to point to those containers.

Scope
-------------

Server, deployment

Installation
-------------

::

    $ docker exec -it mcloud mcloud-plugins install mcloud-plugin-haproxy