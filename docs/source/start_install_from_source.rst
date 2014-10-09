
.. _from_source:


Building from source
-------------------------

.. note::
    Instructions are provided for Ubuntu. Adapt it to your linux distribution by replacing package names andr/or
    command names.

Required packages::

    sudo apt-get update
    sudo apt-get install python-dev python-virtualenv libffi-dev libssl-dev libncurses5-dev libreadline-dev


Install mfcloud packages::

    $ sudo mkdir /opt  # if you don't have it already
    $ sudo virtualenv /opt/mfcloud
    $ sudo /opt/mfcloud/bin/pip install mfcloud

Link mfcloud executables::

    $ sudo ln -s /opt/mfcloud/bin/mfcloud* /usr/local/bin/

Create file /etc/init/mfcloud.conf with follwing contents::

    description "Mfcloud server"
    author "Modera"
    start on filesystem and started docker
    stop on runlevel [!2345]
    respawn
    script
      /opt/mfcloud/bin/mfcloud-rpc-server >> /var/log/mfcloud.log 2>&1
    end script

Start mfcloud service::

    $ sudo service mfcloud start

