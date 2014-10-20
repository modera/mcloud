
==========================================
Container start fine-tuning
==========================================


This chapter will describe the things you should know about mcloud internals,
to feel comfortable when working with it.

Preparations
==============

This time we will take this application::

    mysql:
        image: mysql

    django:
        image: python:2.7.8
        cmd: /usr/src/app/run.sh
        volumes:
          .: /usr/src/app

    web:
        image: nginx
        volumes:
            nginx.conf: /etc/nginx.conf

run.sh is installing some dependencies, and execute database migration on start::

    #!/bin/bash

    pip install -r requirements.txt
    ./manage.py syncdb
    ./manage.py migrate

    if [ "$DJANGO_CONFIGURATION" == "Dev" ]
    then
        echo "Starting django dev server"
        cratis runserver 0.0.0.0:8000
    else
        uwsgi --ini uwsgi.ini
    fi


Starting application
======================

First thing you do when working with mcloud application, you start your application::

    $ mcloud start myapp --init

Init flag says we need to create new application if it's not here.

So, what happens when you start your application?
**It fails!** Saying something like "can't connect to database on host 'mysql' port 3306"

.. note:: You can check logs of container with "mcloud logs {service}.{appname}" command

Now we need to understand some concepts of mcloud to fix this.

Understanding start process
==============================

After start command, mcloud does the following:

- pull or build images that are missing
- create each container according to configuration
- start containers one after another

.. note::
    Containers are started and created in exact same order they are in mcloud.yml

When container mcloud start container, mcloud gives Docker a command to start container,
docker executes the command specified in config and do not give mcloud any real feedback on how execution continue.

So, mcloud assumes all is ok and imidiately continue execution by starting next container.

In our way it works like this:

- mysql started (... but it's continue initializing mysqld daemon, and not ready to accept connections)
- mcloud starts next container
- next is "django", which quickly check dependencies and try to syncronize Database
- as Database is not yet accepting connections, "django" fails

How can we fix this?

Wait directive to the rescue!
===============================

"wait: {number of secconds}"

This directive says mcloud to wait specified amount of seconds, then check if container still alive, and
if yes, only then continue execution::

    mysql:
        image: mysql
        wait: 10s

    django:
        image: python:2.7.8
        cmd: /usr/src/app/run.sh
        volumes:
          .: /usr/src/app

    web:
        image: nginx
        volumes:
            nginx.conf: /etc/nginx.conf

This time, if we start application, we will have pause for 10 seconds on mysql container,
and then execution continue. In this time, for sure, mysql will get enough time to load.

But, 10 seconds... soo long!!

Ok, let's optimize a bit. We all know, that mysql emits "mysqld: ready for connections." when it's
done initializing, so lets use this::

    mysql:
        image: mysql
        wait: 10s for "mysqld: ready for connections."

    django:
        image: python:2.7.8
        cmd: /usr/src/app/run.sh
        volumes:
          .: /usr/src/app

    web:
        image: nginx
        volumes:
            nginx.conf: /etc/nginx.conf

This time, if mysql is loaded, in shorter time (1-2s usually) we will see mcloud will continue execution.

Now, application starting nicely, but there is couple things to improve.

Wait with console helper
===========================

If heathcheck is enabled in nginx, it may complain about not accessible upstream. That's because
on moment when nginx is tarting, it can not connect to our python application.

Let's fix this as well::

    mysql:
        image: mysql
        wait: 10s for "mysqld: ready for connections."

    django:
        image: python:2.7.8
        cmd: /usr/src/app/run.sh
        volumes:
          .: /usr/src/app
        wait: 300s

    web:
        image: nginx
        volumes:
            nginx.conf: /etc/nginx.conf

Things to note here:

- we put 300s int wait, because run.sh may install dependencies, that may be preatty long process
- we don't use "wait ... for" feature, as in production and dev, django is running by different commands,
  so we can't expect any message here.

But wait! Are you really mean we should pause for 300s on django?
No, no. Here how we can fix this... Let's update our run.sh file a bit::


    #!/bin/bash

    pip install -r requirements.txt
    ./manage.py syncdb
    ./manage.py migrate

    @me ready in 3s

    if [ "$DJANGO_CONFIGURATION" == "Dev" ]
    then
        echo "Starting django dev server"
        cratis runserver 0.0.0.0:8000
    else
        uwsgi --ini uwsgi.ini
    fi

"@me ready in 3s" - tells mcloud container is already finished main work and about to start, and it will
happen maximum in 3s.

So, mcloud will:

- start django
- start waiting for 300s
- received "@me reade in 3s" signal
- pause for 3s
- check container is still running and continue execution


Wrap up
================

Now our containers are gently wait for each other, but without spending any extra time
for long waits.

