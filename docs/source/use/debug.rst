
Debugging application
=============================


Run
----------

Running command in container::

    $ mcloud run service.app [command]

Command will create copy of container, mount same volumes and execute command.

Command is "bash" by default, which opens interactive terminal.

Command may be omitted, by default bash is executed.

This will create exact copy of container you are asking to run into and
attach all volumes of this container.

.. note::
    As run command is just make an illusion of connecting into container,
    you can not see processes of target container, and you can't affect data that
    is located outside of volumes.



Logs
------------

Show container logs::

    $ mcloud logs service.app

Show last 100 lines of container log and follow all new logs.
Hit Ctrl+C for exit.


Inspect
-------------

Shows docker inspect for a container::

    $ mcloud inspect service.app

