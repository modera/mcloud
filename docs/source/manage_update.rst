

Updating mCloud
============================================

mCloud install from packages
----------------------------------

To update::

    $ apt-get update && apt-get install mcloud

And restart service::

    $ sudo service mcloud restart


Manualy installed mCloud update
----------------------------------

Update is easy::

    $ apt-get update && apt-get install mcloud

And restart service::

    $ sudo service mcloud restart


Source installed mCloud update
----------------------------------

Update mCloud and dependencies::

    $ sudo /opt/mcloud/bin/pip install -U mcloud

And restart service::

    $ sudo service mcloud restart
