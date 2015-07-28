
============================================
Local application
============================================

Before we deploy our first application, we need to prepare
mcloud by installing haproxy plugin, which will act as load balancer
and stream web content.

Here is how it will look like:

.. uml::

    cloud Internet {

    }

    package Docker {
        [Haproxy] << Load Balancer >>

        [mysql.myapp]
        [php.myapp]
        [nginx.myapp]
        [memcache.myapp]

        nginx.myapp -down-> php.myapp
        php.myapp -down-> mysql.myapp
        php.myapp -down-> memcache.myapp

        Haproxy ..left..> nginx.myapp

    }

    Internet ..left..> Haproxy



Plugin installation
------------------------

Install plugin::

    $ docker exec -it mcloud mcloud-plugins install mcloud-plugin-haproxy
    $ docker restart mcloud


Check logs and wait until mcloud start (it takes some time to download haproxy image)::

    $ docker logs -f mcloud

Make sure haproxy container is started::

    $ docker ps

