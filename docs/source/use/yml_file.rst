
==========================================
mcloud.yml file
==========================================

Every application in ModeraCloud runs inside one or several Docker containers. To describe those containers we  use *mcloud.yml* configuration file.

Syntax is very easy and you may already be familiar with it if you ever tried Docker's Fig.

Example mcloud.yml::

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

Each top level key is the service name. You can give containers any name. It should be short, descriptive, and unique per application. As these are used to create internal hostnames for services please keep in mind to keep the names clear of any special characters.

.. _single_process:
.. note::
    Each container should run only one process. This provides lot of flexibility and ease debugging and application configuration. For example, scaling is not possible if you have more than one process inside containers.


Selecting services to run
==========================

Before configuring containers, you should know what kind of containers you really need.
Here we give several container layouts, to give you an idea what you may need
for your application.


Static web page
-------------------------
Bunch of html files, images, css.

You need a http server that can serve static quickly.

Containers:

- nginx or lighthttpd container (https://registry.hub.docker.com/_/nginx/)

Config::

    nginx:
        image: nginx
        volumes:
            nginx.conf: /etc/nginx.conf
        ...


Dynamic application
--------------------------------
Nodejs/php/python/java backend and some static folder with files (css js).

You may need:

- http server that can serve static quickly
- application server that can handle your application stack
- cron
- database
- cache
- outgoing mail server

Containers:

- nginx or lighthttpd container  (https://registry.hub.docker.com/_/nginx/)
- application server of your choice:
   - for php - php-fpm (https://registry.hub.docker.com/_/php/)
   - for java, tomcat, jetty, etc. (https://registry.hub.docker.com/_/java/)
   - for python, gunicorn, uwsgi, etc.. (https://registry.hub.docker.com/_/python/)
   - for ruby, unicorn .. (https://registry.hub.docker.com/_/ruby/)
   - ...
- cron, same as application server, but specify "cmd: cron -f"
- mysql, postgree, oracle, some other (https://registry.hub.docker.com/_/mysql/)
- postfix (https://registry.hub.docker.com/u/catatnight/postfix/)
- memcache/redis (https://registry.hub.docker.com/_/redis/)

Depending on application complexity, container set may vary, but you get an idea.


In-memory config
==========================

Mcloud stores it's config in redis to prevent problems in case of corrupted or missing
configuration files. Initial configuration is copied into redis database.

There is set of commands you may to update in-memory configuration::

Show difference between file and memory configs::

    $ mcloud config --diff

Update in-memory configs with contents of file::

    $ mcloud config --update

When working with remote server, you should explicitly specify path to .yml file, otherwise
mcloud will show error like "mcloud.yml file not found"::

    $ mcloud -h some.remote.server.com config --diff --config mcloud.yml
    $ mcloud -h some.remote.server.com config --update --config mcloud.yml


Selecting an image for each container
======================================

Main thing to configure is what image to use inside container.
There are two options:

1) Use "image:" to use one of prebuilt containers available in `https://registry.hub.docker.com/`
2) Build your own image with "build:" directive, to specify directory, where
   Dockerfile is stored.
3) Define dockerfile inline using "dockerfile:" directive which accepts yaml multiline literal
   as dockerfile source.


Attaching volumes
=======================

Parts of your containers that contain dynamic data, should be mounted as volumes.

Also volumes allow to synchronize, backup and restore parts of container filesystem.

Examples of when you should use volumes:

- folders where application writes logs should be a volume
- folder where database write it's data - should be a volume
- folder where user content is stored, should be a volue
- folders that need to be shared between container, also should be a volume
- override config files of service or application.

Syntax for volumes is following::

    myservice:
        ...
        volumes:
            {local path}: {path in container}
            {local path}: {path in container}
            {local path}: {path in container}

Example volumes usage:

- ".:/var/app" - Mount project directory as /var/app folder in directory
- "www:/var/www" - Mount www directory ass /var/www inside container
- "nginx.conf:/etc/nginx.conf" - override nginx config with one stored on project directory

Volumes may be used to share files between containers. If you mount same folder into two different containers,
they will see changes of each other.


Command
==============

Every container run single command inside container. Container should run single command, that shouldn't daemonize.

Command to run is specified using "cmd:" directive.

Command is optional, by default command specified in Dockerfile used to build image is executed.

Example commands:

- "cmd: cron -f" - runs cron in foreground mode (remember? don't daemonize)
- "nginx" - just run nginx
- "php-fpm" - runs php process
- "python my_app.py" - runs python application
- "bash run.sh" - execute shell script. In this case, last command of script should be sme long running process.


Bash scripts
----------------

executing bash scripts maybe very useful when you need to do some preparations before actual
application start.

For example, you may install dependencies in bash script, just before app start::

    #!/bin/bash
    # this is statt_my_app.sh

    composer install  # install deps
    php app/console assets:install  # collect static files

    php-fpm  # run php, this will block

Run it as "cmd: bash statt_my_app.sh"


Common rules for command
---------------------------

You can execute anything in container, but several rules should be followed.

Always in foreground
^^^^^^^^^^^^^^^^^^^^^^

Process should stay in foreground, otherwise Docker assumes process is stopped, and terminate container.

Listen on 0.0.0.0
^^^^^^^^^^^^^^^^^^^^^^
If your service listen on some port and meant to be used in other containers, configure it to listen
on external ip address, or other containers will not be able to connect to it.

That happens because, each container is tiny virtual machine with it's own network stack.

Connect to others by short name
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If container needs to connect to other container, it should use short name of other container as a hostname.

Ex, if php needs to reach mysql within container called "mysql", it should connect to host "mysql" port 3306.


Environment variables
========================

Environment variables can be specified with "env:" directive.

Example::

    env:
        MY_NICE_VAR: 123
        ANOTHER: just some text


