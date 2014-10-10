



Installing haproxy
------------------------------

Haproxy is only needed when you install mcloud on remote sever or
if you run mcloud in virtual machine, and want to access applications from
your host machine by domain names like **.mflcoud.lh

Install haproxy::

    $ sudo apt-get install haproxy

Then edit /etc/default/haproxy and set ENABLED=1

Then start haproxy service::

    $ sudo service haproxy start

Also you need to add *--haproxy* option to the mcloud-rpc-server command.
To do this, edit /etc/init/mcloud.conf and add this option to the end::

    exec /opt/mcloud/bin/mcloud-rpc-server --haproxy  >> /var/log/mcloud.log 2>&1

And finally restart mcloud::

    $ service mcloud restart

.. note::

    To use **.mcloud.lh with mcloud inside virtual machine, you also need to configure
    your local machine to use the virtual machine as dns-server, ex.:
    http://stackoverflow.com/questions/138162/wildcards-in-a-hosts-file