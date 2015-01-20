
=====================================
Remote commands
=====================================


Remote commands can be executed using -h flag to specify hostname of mcloud server::

    mcloud -h my.remote.host.com list

All commands that accept "<service>.<app>" notation also accept @host part to specify host name::

    mcloud run php.myapp@myhost.com

