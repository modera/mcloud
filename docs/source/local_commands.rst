
==========================================
Command reference
==========================================

running command basic syntax is::

    $ mcloud command [... arguments ...]

You can also start mcloud in shell mode::

    $ mcloud

Then you can omit "mcloud" prefix.


Overview commands
===================

List
--------------------

List shows all application list::

    $ mcloud list [-f]

command have special flag "-f" (follow) that continuously print status report.

Status
--------------------

Show status of application::

    $ mcloud status app [-f]

command have special flag "-f" (follow) that continuously print status report.

Initialize/remove
=======================

Init
-----------

Initialize new application::

    $ mcloud init [appname] [path]

accepts path as extra argument (by default current directory)
app name is directory name by default.

.. note::
    There is shorthand "start --init", which initialize and start newly created application

Remove
--------------

Removes an application::

    $ mcloud remove

Command will destroy all containers and remove application from MCloud listings.


Application lifecylce
=======================

Syntax
--------------

Lifecycle commands all have common syntax of::

    $ mcloud {command} [service][.app]

Command can be run also without service name, then action will be applied, to
entire application::

    $ mcloud {command} .app

Also, application name may be skipped, then MCloud will try to restore it from context::

    $ mcloud {command} service

In shell mode, current application may be set using "use" command. If no application
is given, then mcloud will use name of current directory as application name.

Commands
--------------------

Commands are:

 - **start** - start application containers, will trigger *create* for containers that are not created yet
 - **stop** - stop application containers
 - **restart** - runs *stop* and *start* sequentially
 - **destroy** - remove application containers, will trigger *stop* for running containers
 - **create** - create application containers without starting them
 - **rebuild** - runs *destroy* and *start* sequentially

**start** has optional --init flag that initialize application if it's not initialized

Order of executions
---------------------

When service name is specified, command is executed on single container.
When only application name given, command is applied on each container in order they appear
in mcloud.yml.

Start is special a bit, it first call "create" on every not-creted container, and when every container exist,
then it starts containers.


Run & debug
================

Run
----------

Running command in container::

    $ mcloud run app.service [command]

Command will create copy of container, mount same volumes and execute command.

Command is "bash" by default, which opens interactive terminal.

Logs
------------

Show container logs::

    $ mcloud logs app.service

Show last 100 lines of container log and follow all new logs.
Hit Ctrl+C for exit.

Inspect
-------------

Shows docker inspect for a container::

    $ mcloud inspect app.service

Volume synchronization
===========================

Syntax
-----------

Synchronize volumes and folders. Syntax is::

    $ mcloud {from} {to} [--no-remove] [--force]

From and to are volume spec.
Spec for remote volume::

    [service.]app@host[:/volume/path]

host may be set to "@me" which is current host.
service and volume name may be skipped, then command assumes it's main volume of application (where mcloud.yml resides)

If volume spec do not match remote volume format, then command assumes, it is
just directory name.

Work order
--------------

Command does the following:

1) Command computes snapshot of source and destination locations by collecting list of files,
   calculating modification time diffs. (time diff = server current time - modification time)
2) Compares result, and if no --force flag, shows diff list to user. (new, updated, removed files)
3) if no --force flag, ask confirmation from user
4) Create archive with new and updated files
5) Transfer archive (progress is displayed)
6) Extract archive
7) if no --no-remove flag, removes files.

Usage patterns
----------------

- local folder to local folder
- remote volume to local folder
- local folder to remote volume
- remote volume to remote volume

Variables
=====================

You can assign extra environment variables that will be passed to containers::

    $ mcloud set VAR_NAME val
    $ mcloud unset VAR_NAME
    $ mcloud vars

.. note::
    Variables are assigned on container creation, so you need to rebuild container if you
    need changes to be applied on running container.

Application publishing
===========================

**Publish** application to url::

    $ mcloud publish app my_domain.com [--ssl]

--ssl means https://my_domain.com

.. note::
    You should publish both --ssl and non-ssl version of url, if your application handles two protocols.

**Unpublish** is::

    $ mcloud publish my_domain.com [--ssl]

Application name is not needed.


