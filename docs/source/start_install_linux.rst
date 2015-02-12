

===================================
Install on Linux
===================================

.. note::
    Currently we provide packages for Ubuntu Trusty(14.04), Precise(12.04) and Lucid(10.04).
    If you need to install ModeraCloud on any other version follow: :ref:`from_source`


What will be installed?
===========================

install.sh:

- installs mcloud && haproxy ppa keys
- installs docker
- install mcloud-full package

mcloud-full package:

- Redis
- Haproxy
- Dnsmasq

If you need to override anything mentioned above please follow :ref:`manual_install`.


ModeraCloud installation
==========================

Execute the installation script::

    curl https://mcloud.io/install.sh | sudo sh


Verify installation
===========================ModeraCloud======

Just start ModeraCloud shell::

    $ mcloud

    mcloud: ~@me>

Hit Ctrl+D to exit.
