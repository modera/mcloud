
.. _from_source:


Installing mcloud from source
------------------------------

.. note::
    Instructions are provided for Ubuntu. Adapt it to your linux distribution by replacing package names andr/or
    command names.

Required packages::

    sudo apt-get update
    sudo apt-get install python-dev python-virtualenv libffi-dev libssl-dev libncurses5-dev libreadline-dev


Install mcloud packages::

    $ sudo mkdir /opt  # if you don't have it already
    $ sudo virtualenv /opt/mcloud
    $ sudo /opt/mcloud/bin/pip install mcloud

Link mcloud executables::

    $ sudo ln -s /opt/mcloud/bin/mcloud* /usr/local/bin/

Create file /etc/init/mcloud.conf with follwing contents::

    description "Mcloud server"
    author "Modera"
    start on filesystem and started docker
    stop on runlevel [!2345]
    respawn
    script
      /opt/mcloud/bin/mcloud-server >> /var/log/mcloud.log 2>&1
    end script

Start mcloud service::

    $ sudo service mcloud start

