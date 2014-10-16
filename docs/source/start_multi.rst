
===============================================
Deploying multicontainer appication
===============================================


.. note::
    You can get example code in "flask-redis" folder from our samples repository https://github.com/modera/mcloud-samples/


This time we will deploy bit more complex application, that have several containers, that
communicate to each-other.

Spec
----------------------

Deploy flask application that will store number of pageviews in redis.

Files overview
=========================

mcloud.yml file
----------------------

yml file have several services::

    redis:
        image: redis

    flask:
        image: python:2.7.8
        cmd: /usr/src/app/run.sh
        volumes:
          .: /usr/src/app
        wait: 100

    web:
        image: nginx

        volumes:
            nginx.conf: /etc/nginx.conf


Things to note:

- "python:2.7.8" you can use docker tag, to specifyu exact version of container
- you can mount not only directories, but also single files (nginx.conf)
- :ref:`wait` is used

app.py
------------------

This is just trivial flask application::

    from flask import Flask
    app = Flask(__name__)

    from redis import Redis
    redis = Redis(host='redis')

    @app.route("/")
    def hello():
        views = redis.incr('views')
        return "<h1>Hello, MCloud!</h1><p>Page opened: %d times</p>" % views

    if __name__ == "__main__":
        app.debug = True
        app.run(host='0.0.0.0')

Except couple things:

- run on 0.0.0.0 means application will listen on all available ips. :ref:`localhost`
- "Redis(host='redis')" - redis hostname is "redis".  :ref:`dns`

nginx.conf
----------------

Nginx config is really minimal::

    worker_processes  1;

    events {
        worker_connections  1024;
    }


    http {
        upstream app {
            server flask:5000;
        }

        server {
            listen 80 default_server;

            location / {
                proxy_pass http://app;
            }
        }
    }

    daemon off;

Couple points here:

- "daemon off" - nginx is only process in container, so no need to daemonize. :ref:`single_process`
- "server flask:5000;" - see :ref:`dns`
- proxy_pass is passing to upstream, upstream then resolves "flask" to ip address.


requirements.txt
-------------------------------

Just couple dependencies there::

    Flask
    redis

run.sh
-----------------------

As we need to install/update dependencies when application start, it's more convinient to execute sh
script as main process::

    #!/bin/bash
    cd /usr/src/app

    pip install -r requirements.txt

    @me ready in 1s
    python app.py

One thing, to note is "@me ready in 1s", which gives mcloud signal, application is finnished installing dependencies,
and started (or crashed?) in 1 second. Se more in :ref:`wait`

Running application
=======================

No applications running now::

    $ mcloud list

    +------------------+--------+-------+--------+-----+------+
    | Application name | status | cpu % | memory | Web | Path |
    +------------------+--------+-------+--------+-----+------+


Start application::

    $ mcloud start --init

    [2861] Starting application
    [2861] Got response
    [2861] Service redis.flask-redis is not created. Creating
    [2861] Service flask.flask-redis is not created. Creating
    [2861] Service web.flask-redis is not created. Creating

    **************************************************

     Service redis.flask-redis

    **************************************************
    [2861] Service redis.flask-redis is not running. Starting
    [2861][redis.flask-redis] Starting service
    [2861][redis.flask-redis] Service resolve by name result: 30e34001b8733dee39672e48da880d5fe7ed69bc08b3a75218e3f020a8085ad0
    [2861][redis.flask-redis] Starting service...
    Startng container with config: {'Binds': ['/var/run/mcloud:/var/run/mcloud', '/home/alex/dev/mcloud/mcloud/api.py:/usr/bin/@me'], 'DnsSearch': u'flask-redis.mcloud.lh', 'Dns': ['172.17.42.1']}
    Updating container list

    **************************************************

     Service flask.flask-redis

    **************************************************
    [2861] Service flask.flask-redis is not running. Starting
    [2861][flask.flask-redis] Starting service
    [2861][flask.flask-redis] Service resolve by name result: 9f69ead32b1bbeb9563dce31df91f202a2f1bd1857f439b4ad497535f02ac269
    [2861][flask.flask-redis] Starting service...
    Startng container with config: {'Binds': ['/home/alex/dev/mcloud-samples/flask-redis/.:/usr/src/app', '/var/run/mcloud:/var/run/mcloud', '/home/alex/dev/mcloud/mcloud/api.py:/usr/bin/@me'], 'DnsSearch': u'flask-redis.mcloud.lh', 'Dns': ['172.17.42.1']}
    Updating container list
    Waiting for container to start. with timout 100s
    Downloading/unpacking Flask (from -r requirements.txt (line 1))
    ...
    Downloading/unpacking redis (from -r requirements.txt (line 2))
    ...
    Downloading/unpacking Werkzeug>=0.7 (from Flask->-r requirements.txt (line 1))
    ...
    Downloading/unpacking Jinja2>=2.4 (from Flask->-r requirements.txt (line 1))
    ...
    Downloading/unpacking itsdangerous>=0.21 (from Flask->-r requirements.txt (line 1))
    ...
    Downloading/unpacking markupsafe (from Jinja2>=2.4->Flask->-r requirements.txt (line 1))
    ...
    Installing collected packages: Flask, redis, Werkzeug, Jinja2, itsdangerous, markupsafe
    ...
    Successfully installed Flask redis Werkzeug Jinja2 itsdangerous markupsafe

    Cleaning up...

    Container is waiting 1.0s to make sure container is started.
     * Running on http://0.0.0.0:5000/

     * Restarting with reloader

    Container still up. Continue execution.

    **************************************************

     Service web.flask-redis

    **************************************************
    [2861] Service web.flask-redis is not running. Starting
    [2861][web.flask-redis] Starting service
    [2861][web.flask-redis] Service resolve by name result: 66ac5243b38b7822c7005666fa84d56c33e3e04aa76d6270e467a223c35d99ab
    [2861][web.flask-redis] Starting service...
    Startng container with config: {'Binds': ['/home/alex/dev/mcloud-samples/flask-redis/nginx.conf:/etc/nginx.conf', '/var/run/mcloud:/var/run/mcloud', '/home/alex/dev/mcloud/mcloud/api.py:/usr/bin/@me'], 'DnsSearch': u'flask-redis.mcloud.lh', 'Dns': ['172.17.42.1']}
    Updating container list
    result: u'Done.'


Now let's check it's running::

    $ mcloud list

    +------------------+---------+-------+--------+--------------------------------+-------------------------------------------+
    | Application name |  status | cpu % | memory |              Web               |                    Path                   |
    +------------------+---------+-------+--------+--------------------------------+-------------------------------------------+
    |   flask-redis    | RUNNING | 4.20% |  38M   | flask-redis.mcloud.lh -> [web] | /home/alex/dev/mcloud-samples/flask-redis |
    +------------------+---------+-------+--------+--------------------------------+-------------------------------------------+

    $ mcloud status flask-redis

    +-------------------+--------+-------------+-------+--------+-----------------+-------------------------------+
    |    Service name   | status |      ip     | cpu % | memory |     volumes     |          public urls          |
    +-------------------+--------+-------------+-------+--------+-----------------+-------------------------------+
    | redis.flask-redis |   ON   | 172.17.0.54 | 0.46% |   6M   |      /data      |                               |
    +-------------------+--------+-------------+-------+--------+-----------------+-------------------------------+
    | flask.flask-redis |   ON   | 172.17.0.55 | 4.80% |  30M   |   /usr/src/app  |                               |
    +-------------------+--------+-------------+-------+--------+-----------------+-------------------------------+
    |  web.flask-redis  |   ON   | 172.17.0.56 | 0.00% |   2M   | /etc/nginx.conf | http://flask-redis.mcloud.lh/ |
    +-------------------+--------+-------------+-------+--------+-----------------+-------------------------------+

Now, if we open url in browser you will see simple page-veiw counter, that takes data from redis.





