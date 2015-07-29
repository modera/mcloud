
============================================
Deploying simple 1-container application
============================================

.. note::

    Sources of this example are at https://github.com/modera/mcloud-samples/tree/master/hello

We deploy simple application with nginx as web-server an single html page.

Here is how our configuration will look like:

.. uml::

    cloud Internet {

    }

    package Docker {
        [Haproxy] << Load Balancer >>

        [nginx.myapp]

        Haproxy ..left..> nginx.myapp

    }

    Internet ..> Haproxy


Initial configuration
------------------------

mcloud.yml::

    web:
        web: 80
        image: nginx:latest

        volumes:
            public: /usr/share/nginx/html


"web: 80" - means that this container will provide a web service on port 80.

Image - docker image from https://registry.hub.docker.com/_/nginx/

volumes - defines that directory public will be mapped into "/usr/share/nginx/html" on nginx container.

Application start
--------------------

Let's start the application::

    $ git clone git@github.com:modera/mcloud-samples.git
    $ cd mcloud-samples/hello
    $ mcloud start --init

    Using folder name as application name: hello

    [125] Starting application
    [125] Got response
    [125] Service web.hello is not created. Creating

    **************************************************

     Service web.hello

    **************************************************
    [125] Service web.hello is not running. Starting
    [125][web.hello] Starting service
    [125][web.hello] Service resolve by name result: 97386c42e961707d1a65f34c0181aec401b82c0e6d0db0c53eccf841085045aa
    [125][web.hello] Starting service...
    Startng container. config: {'ExtraHosts': [u'web:None'], 'Binds': [u'/home/alex/dev/mcloud-samples/hello/public:/usr/share/nginx/html', u'/root/.mcloud/volumes/web.hello/_var_cache_nginx:/var/cache/nginx']}
    Emit startup event
    Call start listener <mcloud_haproxy.HaproxyPlugin object at 0x7fb48c0f8710>
    Updating haproxy configUpdating haproxy config on deployment localupdated local - OKUpdating container list
    result: u'Done.'

Now we can check application status::

    $ mcloud status

    Using folder name as application name: hello


    +--------------+--------+-------------+-------+--------+-----------------------+-------------------------+
    | Service name | status |      ip     | cpu % | memory |        volumes        |       public urls       |
    +--------------+--------+-------------+-------+--------+-----------------------+-------------------------+
    |  web.hello   |   ON   | 172.17.1.96 | 0.00% |   0M   |    /var/cache/nginx   | http://hello.mcloud.lh/ |
    |              |        |             |       |        | /usr/share/nginx/html |                         |
    +--------------+--------+-------------+-------+--------+-----------------------+-------------------------+

We can see our application with it's only container is running and have public url.
Ctrl + click on it, to open it in browser.

.. note::

    You may notice that, mcloud shows "Using folder name as application name: hello" when starting application. You can
    read about application naming conventions in CLI reference

Application names & basic commands
-------------------------------------

You

If you don't see "Hello, mcloud!", then go back to Installation chapter to make sure haproxy & dnsmasq are configured correctly.

