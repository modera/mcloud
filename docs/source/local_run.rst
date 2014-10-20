
=======================================
Running commands inside containers
=======================================

If you need to run some commands in container, you may use run command::

    $ mcloud run appname service [command]

Command may be omitted, by default bash is executed.

This will create exact copy of container you are asking to run into and
attach all volumes of this container.

.. note::
    As run command is just make an illusion of connecting into container,
    you can not see processes of target container, and you can't affect data that
    is located outside of volumes.


