
===============================================
Deploying hello website
===============================================

assume we have a hello web-page, that we want to deploy
as mcloud application::

    <!DOCTYPE html>
    <html>
    <head>
        <title></title>
    </head>
    <body>
        Hello, mcloud!
    </body>
    </html>


To deploy this we need the following mcloud.yml configuration::

    web:
        image: orchardup/nginx

        volumes:
            public: /var/www


This will create one service called "web".
We use "orchardup/nginx" image that contains nginx that serve everything inside /var/www directory.

In mcloud.yml we specify, that we will mount current directory to /var/www volume inside container.
So, our public directory will be accessible from web.

Application structure is following::

 - public
    - index.html
 - mflcoud.yml

Now, start mcloud shell::

    $ mcloud

mcloud will show command prompt::

    mcloud: ~@me>


Now we can init our application with "init" command::

    mcloud: ~@me> init hello

"hello" is name of our application.

List command will show our newly created application::

    mcloud: ~@me> list

    +------------------+--------+-------+--------+-------------------------------+----------------------------+
    | Application name | status | cpu % | memory |              Web              |            Path            |
    +------------------+--------+-------+--------+-------------------------------+----------------------------+
    |      hello      |        |       |        | hello.mcloud.lh -> [No web] | /home/alex/dev/mcloud/tmp |
    +------------------+--------+-------+--------+-------------------------------+----------------------------+

We can "use" new application, so we don't need to typ application name every time::

    mcloud: ~@me>  use hello

    mcloud: hello@me>

Now, lets start our application::

    mcloud: hello@me>  start
    hello None
    [2646] Starting application
    [2646] Got response
    [2646] Service web.hello is not created. Creating

    **************************************************

     Service web.hello

    **************************************************
    [2646] Service web.hello is not running. Starting
    [2646][web.hello] Starting service
    [2646][web.hello] Service resolve by name result: 72e364366f1c536b35d602e7c5c29449e65af9094c12d5118f3720a88e4c3d50
    [2646][web.hello] Starting service...
    Startng container with config: {'Binds': ['/home/alex/dev/mcloud/tmp/public:/var/www', '/var/run/mcloud:/var/run/mcloud', '/home/alex/dev/mcloud/mcloud/api.py:/usr/bin/@me'], 'DnsSearch': u'hello.mcloud.lh', 'Dns': ['172.17.42.1']}
    Updating container list
    result: u'Done.'

    mcloud: hello@me>


And list will show the following::

    mcloud: hello@me>  status

    +--------------+--------+------------+-------+--------+----------+--------------------------+
    | Service name | status |     ip     | cpu % | memory | volumes  |       public urls        |
    +--------------+--------+------------+-------+--------+----------+--------------------------+
    |  web.hello  |   ON   | 172.17.0.2 | 0.07% |  12M   | /var/www | http://hello.mcloud.lh |
    +--------------+--------+------------+-------+--------+----------+--------------------------+


More detailed info about current application::


Couple of things to notice from the output:
- application is now in running state
- assigned IP address is 172.17.0.2
- the web container is detected to expose port 80 thus it is mapped to special internal domain address hello.mcloud.lh


Lets use Curl to load the web page (in separate terminal)::

    $ curl 172.17.0.2

    <!DOCTYPE html>
    <html>
    <head>
        <title></title>
    </head>
    <body>
        Hello, mcloud!
    </body>
    </html>

You should see same output if you use::

    $ curl hello.mcloud.lh


Stopping and removing an app
---------------------------------------

Stop the application::

    mcloud: hello@me>  stop
    [2649] Stoping application
    [2649] Got response
    [2649] Service web.hello is running. Stoping
    result: u'Done.'


Now we see that web.service is OFF, it means that there is container created, but it’s not running. When application is stopped, it preserves all the data that was in container.
If you need to remove the data but keep the application in registry, run::

    mcloud: hello@me>  destroy hello
    [2650] Destroying application containers
    [2650] Got response
    [2650] Destroying container: None
    [2650] Service web.hello container is created. Destroying
    result: u'Done.'

If you need to remove all traces of the application, run::

    mcloud: hello@me>  remove hello
    [2651] Destroying application containers
    [2651] Got response
    [2651] Destroying container: None
    [2651] Service web.hello container is not yet created.
    result: u'Done.'
