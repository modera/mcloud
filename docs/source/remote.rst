



Installing haproxy
------------------------------

Haproxy is only needed when you install mfcloud on remote sever or
if you run mfcloud in virtual machine, and want to access applications from
your host machine by domain names like **.mflcoud.lh

Install haproxy::

    $ sudo apt-get install haproxy

Then edit /etc/default/haproxy and set ENABLED=1

Then start haproxy service::

    $ sudo service haproxy start

Also you need to add *--haproxy* option to the mfcloud-rpc-server command.
To do this, edit /etc/init/mfcloud.conf and add this option to the end::

    exec /opt/mfcloud/bin/mfcloud-rpc-server --haproxy  >> /var/log/mfcloud.log 2>&1

And finally restart mfcloud::

    $ service mfcloud restart

.. note::

    To use **.mfcloud.lh with mfcloud inside virtual machine, you also need to configure
    your local machine to use the virtual machine as dns-server, ex.:
    http://stackoverflow.com/questions/138162/wildcards-in-a-hosts-file