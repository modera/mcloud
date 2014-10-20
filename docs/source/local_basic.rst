
==========================================
Basic commands
==========================================

Initialization
======================

When you create a new application, or checkout it from VCS, you should initialize this
and then start::

    $ mcloud init [appname] [path]
    $ mcloud start appname

Initialization and start in one command::

    $ mcloud start [appname] --init

If app name is not specified, mcloud use folder name.

Restart
=======================

If you application have no autoreload posibility (like python, some java, and other apps)
you usually need to restart your application::

    $ mcloud restart appname [service]

.. note::
    Make sure to restart dependent services as well, because containers change it's ip address
    when restarting. Example, if you restart application server, you should restart nginx as well.

Rebuild
========================

If you change something in mcloud.yml file you may need to rebuild application::

    $ mcloud rebuild appname [service]

mcloud will: destroy each container, create it again, start.

.. danger::::
    You data will keep safe if it iss mounted into volume, otherwise it get Destroyed!


Start/stop
========================

Start and stop allow not to waste resources for not used application.

    $ mcloud stop appname [service]


Logs
========================

Observe logs::

    $ mcloud stop appname [service]
