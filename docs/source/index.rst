
==============
Mcloud Cloud
==============

Welcome to *MCloud* - a tool that helps you manage Docker based deployments.

.. note:: Don't even try to install/use mfcloud until you fill comfortable using docker natively.

Quick Intro
--------------

This simple yml file (mfcloud.yml) will spin out a set of docker containers for you::


    mysql:
        image: mysql

    elasticsearch:
        image: dockerfile/elasticsearch

    postfix:
        image: previousnext/postfix

    redis:
        image: redis

    memcache:
        image: tutum/memcached

    app:
        build: .mfcloud/app
        volumes:
            .: /var/app

    web:
        build: .mfcloud/nginx
        volumes:
            .: /var/app

As you see there is everything that is needed for big Django-based web-shop: Django application (app), nginx load balancer (web),
set of caching services (redis, memcach, elasticsearch, mysql) and mysql database (mysql).

Every container can reach each other by hostname, and it's same in Dev and in production. For Django you will hardcode something like::

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'mydbname',
            'USER': 'mydbuser',
            'PASSWORD': '123123',
            'HOST': 'mysql',
            'PORT': '3306',
        },
    }

After run::

    $ mfcloud init myapp
    $ mfcloud start myapp

You will get this nice overview::
 
    $ mfcloud list

    +------------------+------------------------------+---------+-------+--------+-------------------------------------------------------------------+
    | Application name |             Web              |  status | cpu % | memory |                              services                             |
    +------------------+------------------------------+---------+-------+--------+-------------------------------------------------------------------+
    |     myapp        |   myapp.mfcloud.lh -> [web]  | RUNNING | 0.01% |   5M   |   mysql.myapp   (ON) ip: 172.17.0.2 vol: 49153 (/var/lib/mysql)   |
    |                  |                              |         | 0.09% |  235M  |    elasticsearch.myapp   (ON) ip: 172.17.0.4 vol: 49154 (/data)   |
    |                  |                              |         | 0.01% |   4M   |           postfix.myapp   (ON) ip: 172.17.0.6 vol: 49155          |
    |                  |                              |         | 0.03% |   0M   |        redis.myapp   (ON) ip: 172.17.0.8 vol: 49156 (/data)       |
    |                  |                              |         | 0.00% |   0M   |          memcache.myapp   (ON) ip: 172.17.0.10 vol: 49157         |
    |                  |                              |         | 1.82% |  26M   |       app.myapp   (ON) ip: 172.17.0.12 vol: 49158 (/var/app)      |
    |                  |                              |         | 0.01% |   1M   | web.myapp  * (ON) ip: 172.17.0.14 vol: 49159 (/var/app, /var/www) |
    |                  |                              |         | ----- | -----  |                                                                   |
    |                  |                              |         | 1.96% |  271M  |                                                                   |
    +------------------+------------------------------+---------+-------+--------+-------------------------------------------------------------------+

And sure it's available in your browser as myapp.mfcloud.lh

Impressed? It's not all.

Let's deploy this to production::

    $ mfcloud -h my-remote-mfcloud-server.com init my-remote-app
    $ mfcloud -h my-remote-mfcloud-server.com start my-remote-app
    $ mfcloud -h my-remote-mfcloud-server.com publish mydomain.com web.my-remote-app


And now your app running in production!

What about update? ... Just push volume with code and restart the server::

    $ mfcloud -h my-remote-mfcloud-server.com push my-local-dir-with-code web.my-remote-app:/var/app
    $ mfcloud -h my-remote-mfcloud-server.com restart my-remote-app


In this documentation chapters we will see how to install mfcloud localy, prepare production server, how to configure
your applications and do many usefull tricks with mfcloud and docker containers.

Other features
------------------------------------------

On surface:

 * central place where all projects on your machine listed
 * displays resource usage (CPU and memory) for every application and container
 * easy local-dsn based service discovery
 * login into your containers without SSH server inside (`mfcloud run` command)
 * haproxy-based load balancer
 * SSL-support for production web-sites
 * server-wide environment variables
 * Openssl certificate based security for remote mfcloud servers

Under-the-hood:

 * python + twisted
 * redis, docker, haproxy
 * twisted Docker API implementation (mfcloud own solution)
 * own DNS server
 * websocket-based API, easy to connect from web-browser (Write you own AngularJS based Web-UI ...? )
 * plugin-subsystem + event system + dependency injection = easy to extend


Contents
------------------

.. toctree::
  :maxdepth: 3


  install
  usage
  tutor/static
  examples
  cli
  yml
  dev

.. image:: _static/mfcloud.png



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
