
===============================================
Deploying static website
===============================================

assume we have a static web-page, that we want to deploy
as mfcloud application::

    <!DOCTYPE html>
    <html>
    <head>
        <title></title>
    </head>
    <body>
        Hello, mfcloud!
    </body>
    </html>


To deploy this we need the following mfcloud.yml configuration::

    web:
        image: orchardup/nginx

        volumes:
            public: /var/www


This will create one service called "web".
We use "orchardup/nginx" image that contains nginx that serve everything inside /var/www directory.

In mfcloud.yml we specify, that we will mount current directory to /var/www volume inside container.
So, our public directory will be accessible from web.

Application structure is following::

 - public
    - index.html
 - mflcoud.yml

Now we can init our application with "init" command::

    $ mfcloud init static ./docs/source/samples/source/static

    +------------------+-----+--------+--------------------------+
    | Application name | Web | status |         services         |
    +------------------+-----+--------+--------------------------+
    |      static      |     |        | web.static (NOT CREATED) |
    +------------------+-----+--------+--------------------------+

Here you see application list that are running on your machine.
Same listing you may get by calling `mfcloud list` command.

In listing above you see that we have "static" application that have one service "web.static".
That have no containers created yet.

You can make it sure by typing::

    $ docker ps

    CONTAINER ID        IMAGE               COMMAND             CREATED             STATUS              PORTS               NAMES

You see empty line, that means there is no containers running.

Now, lets start our application::

    $ mfcloud start static

    +------------------+----------------------------+---------+--------------------------------------------------------+
    | Application name |            Web             |  status |                        services                        |
    +------------------+----------------------------+---------+--------------------------------------------------------+
    |      static      | static.mfcloud.lh -> [web] | RUNNING | web.static* (ON) ip: 172.17.0.10 vol: 49153 (/var/www) |
    +------------------+----------------------------+---------+--------------------------------------------------------+

Now, there is a lot more information.

First, the status column shows "RUNNING" status for our application.

Services column also shows that our "web.static" service is running now, it's ip is 172.17.0.10
(also there is volumes information, but it's not important right now).

Web column shows that mfcloud has detected that container exposes port 80, so it's assigned special internal domain
"static.mfcloud.lh" to web.static service port 80.

Let's check what docker shows now::

    $ docker ps

    CONTAINER ID        IMAGE                    COMMAND             CREATED             STATUS              PORTS                   NAMES
    07281278f924        ribozz/rsync:latest      /sbin/my_init       4 minutes ago       Up 4 minutes        0.0.0.0:49153->22/tcp   _volumes_web.static
    a4fb7033d27f        orchardup/nginx:latest   nginx               4 minutes ago       Up 4 minutes        80/tcp                  web.static

.. note::
    Docker containers have same name as your service, so we see here a container with name "web.static". This
    container naming conventions simplify debugging, you can use standard docker tools, to understand what's up
    if something wrog happens with your container.

We have two containers running: one is our service, another is pairing container that allows to upload and download
docker volumes. Read `volumes` section of this documentation for details.


Now, if we open service ip in browser, it will show us index.html contents::

    $ curl 172.17.0.10

    <!DOCTYPE html>
    <html>
    <head>
        <title></title>
    </head>
    <body>
        Hello, mfcloud!
    </body>
    </html>

Same thing happens if we open url assigned by mfcloud::

    $ curl static.mfcloud.lh

    <!DOCTYPE html>
    <html>
    <head>
        <title></title>
    </head>
    <body>
        Hello, mfcloud!
    </body>
    </html>

Url "static.mfcloud.lh" is composed of two parts: [service.appname].[suffix],
suffix in our case is "mfcloud.lh" and "static" is application name.

You can also open same page by specifying direct url that is assigned to service::

    $ curl web.static.mfcloud.lh

    <!DOCTYPE html>
    <html>
    <head>
        <title></title>
    </head>
    <body>
        Hello, mfcloud!
    </body>
    </html>

Now, we can stop the application::

    $ mfcloud stop static

    +------------------+-----+--------+------------------+
    | Application name | Web | status |     services     |
    +------------------+-----+--------+------------------+
    |      static      |     |        | web.static (OFF) |
    +------------------+-----+--------+------------------+

Now we see that web.service is OFF, it means that there is container created, but it's not running.
When application is stoped, it preserves all the data that was in container.

If you need to remove it completely::

    $ mfcloud destroy static

    +------------------+-----+--------+--------------------------+
    | Application name | Web | status |         services         |
    +------------------+-----+--------+--------------------------+
    |      static      |     |        | web.static (NOT CREATED) |
    +------------------+-----+--------+--------------------------+

And now you can remove not needed application completely::

    $ mfcloud remove static

    +------------------+-----+--------+----------+
    | Application name | Web | status | services |
    +------------------+-----+--------+----------+



