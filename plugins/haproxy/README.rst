Haproxy publishing
============================

Haproxy plugin install haproxy as a load balancer for mcloud. Plugin is useful when you need
deploy multiple applications on one server, or use complex application publishing


Multiple applications
-------------------------

.. uml::

    cloud Internet {

    }

    package Docker {
        [Haproxy] << Load Balancer >>

        database App1 {
            [nginx.myapp]
            [another.myapp]
            [something.myapp]
        }

        database App2 {
            [nginx.another]
            [another.another]
        }

        Haproxy ..> nginx.myapp
        Haproxy ..> nginx.another

    }

    Internet ..> Haproxy


Multiple versions
-------------------------


.. uml::

    cloud Internet {

    }

    package Docker {
        [Haproxy] << Load Balancer >>

        [nodejs.app_v1]
        [nodejs.app_v2]

        Haproxy ..> nodejs.app_v1
        Haproxy -> nodejs.app_v2
    }

    Internet ..> Haproxy


Haproxy template
-----------------------

You can use your own template by placing it in /root/.mcloud/haproxy.tpl. Mcloud kindly places default config there.

.. highlights::

    Template is Jinja2 template http://jinja.pocoo.org/docs/

To apply your changes to template restart mcloud::

    $ docker restart mcloud

Default tamplate
^^^^^^^^^^^^^^^^^^

.. literalinclude:: mcloud_haproxy.py
   :lines: 21-94
   :language: jinja


