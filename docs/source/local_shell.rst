
===================
Mcloud shell
===================

MCloud shell simplify usage of remote deployments, and as well may be used
locally to shorten commands, if you mostly work with one application.

shell saves you time in following:

- you don't need to type mcloud prefix every time
- command execution is faster (especially if you execute commands remotely)
- use command allows not to type host name or application name

Start shell
--------------

To execute mcloud command without arguments::

    $ mcloud


Exit shell
--------------

mcloud command will not react to Ctrl + C command. Instead you should type "exit" or
hit Ctrl + D.


Use application
----------------------

Use command allow to omit application name, when executing some commands::

    mcloud> use myapp

    mcloud> status
    mcloud> start
    mcloud> stop

System commands
-------------------------

Anything that starts with "!" is executed as system command::

    mcloud> !ls

    ... list files ...

If you need to execute set of commands, you can run bash::

    mcloud> !bash

To exit, just hit Ctrl+D, and you ar back in mcloud.
If you messed up, see `http://www.imdb.com/title/tt1375666/` for reference.

Switching to remote server
----------------------------

If you need to execute commands on remote machine, isue use command with host::

    mcloud> use @myserver.com

You can combine use remote server with application name::

    mcloud> use myapp@myserver.com

To switch back to local server::

    mcloud> use @







