
==========================================
Command-line reference
==========================================

ModeraCloudCloud command-line basic syntax is::

    $ mcloud command [... arguments ...]

You can also start mcloud in shell mode::

    $ mcloud

Then you can omit *mcloud* prefix.


Overview commands
=======================

Overview commands are about application / service configuration.


List
--------------

List shows all application list::

    $ mcloud list [-f]

Command have special flag "-f" (follow) that continuously print status report.


Status
--------------

Show status of application::

    $ mcloud status app [-f]

Command have special flag "-f" (follow) that continuously print status report.


Init
--------------

Initialize new application::

    $ mcloud init [appname] [path] [--config]

Accepts path as extra argument (by default current directory)
app name is directory name by default.

You can specify configuration file explicitly with --config.

.. note::
    There is shorthand "start --init", which initialize and start newly created application

In case of remote server command will also upload files there. You may interrupt this process and complete it later manually.


Config
--------------

Updates and displays mcloud.yml configuration.

    $ mcloud config [appname] [--config] [--set-env] [--diff]

Examples::

    $ mcloud config mysqapp                   # shows current configuration
    $ mcloud config mysqapp --set-env prod    # set environment to prod
    $ mcloud config mysqapp --update          # reloads configuration
    $ mcloud config mysqapp --diff            # shows difference between current config and mcloud.yml file


Remove
--------------

Removes an application::

    $ mcloud remove

Command will destroy all containers and remove application from app-list.

.. note:: This command still will not remove any application volumes (ex. /var/lib/mysql for mysql container).

To remove application data completely, specify --purge flag::

    $ mcloud remove --purge


Application lifecycle
=======================

Application lifecycle commands operate in scope of an application or its services.

They all have common syntax of::

    $ mcloud {command} [service.][app]

Command can be run also without service name, then action will be applied to
entire application::

    $ mcloud {command} app

Also, application name mModeraCloudskipModeraCloudhen ModeraCloud will try to restore it from context::

    $ mcloud {command} service.

Note the dot(".") at the end, it specify it's service name not the application.

In shell mode, current application may be set using "use" command. If ModeraCloudlication
ModeraClouden, then ModeraCloud will use name of current directory name as application name.

When service name is specified, command is executed on single container. When only application name given, command is applied on each container in order they appear in *mcloud.yml*.


Create
----------

Create application containers without starting them.


Start
----------

Start application containers, will trigger *create* for containers that are not created yet. Once all containers exist it starts them.
ModeraClouds optional --iModeraCloudag that tells ModeraCloud to initialize the application if it's not there.


Stop
----------

Stop application containers.


Restart
----------

Runs *stop* sequentially on all services, then *start* again.


Destroy
----------

Remove application containers. Triggers *stop* for running containers beforehand.

Rebuild
----------

Runs *destroy* on all services. Then *start* again.


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

Volume commands are about controlling the service volumes and data synchronization.


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

#. Command computes snapshot of source and destination locations by collecting list of files,
   calculating modification time diffs. (time diff = server current time - modification time)
#. Compares result, and if no --force flag, shows diff list to user. (new, updated, removed files)
#. if no --force flag, ask confirmation from user
#. Create archive with new and updated files
#. Transfer archive (progress is displayed)
#. Extract archive
#. if no --no-remove flag, removes files.


Usage patterns
----------------

- local folder to local folder
- remote volume to local folder
- local folder to remote volume
- remote volume to remote volume


Environment variables
=====================

You can assign extra environment variables that will be passed to containers::

    $ mcloud set VAR_NAME val
    $ mcloud unset VAR_NAME
    $ mcloud vars

Variables are assigned on container *creation*, so you need to rebuild container if you need changes to be applied on running container.


Application publishing
===========================

Commands are about assigning the public URLs to the applications, which essentially is often the way how the newly deployed applications get "published" or "unpublished".


Publish
-----------

Assign URL to an application::

    $ mcloud publish app my_domain.com [--ssl]

--ssl means https://my_domain.com

.. note::
    You should publish both SSL and non-SSL version of URL if your application handles two protocols.


Unpublish
-----------

Remove an URL assignment from an application::

    $ mcloud unpublish my_domain.com [--ssl]

Application name is not needed.
