


Environment variables
=====================

You can assign extra environment variables that will be passed to containers::

    $ mcloud set VAR_NAME val
    $ mcloud unset VAR_NAME
    $ mcloud vars

Variables are assigned on container *creation*, so you need to rebuild container if you need changes to be applied on running container.

