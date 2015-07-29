
=============================
Working with applications
=============================


Application status
=======================


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


Application lifecycle
==============================

.. uml::

    (*) --> [init] Not created
    "Not created" --> [create] Created
    Created --> [destroy] "Not created"
    "Not created" --> [remove] (*)
    Created --> [start] Started
    Started --> [stop] Created

.. note::

    If aplication or service is in state that requires more actions to get desired state, those actions will
    be performed. Ex. if to **remove** Started application, then **stop**, **destroy** and **remove** commands will be
    executed sequentially.

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


Remove
--------------

Removes an application::

    $ mcloud remove

Command will destroy all containers and remove application from app-list.

.. note:: This command still will not remove any application volumes (ex. /var/lib/mysql for mysql container).

To remove application data completely, specify --purge flag::

    $ mcloud remove --purge



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



Configuration change
======================


Config
--------------

Updates and displays mcloud.yml configuration.

    $ mcloud config [appname] [--config] [--set-env] [--diff]

Examples::

    $ mcloud config mysqapp                   # shows current configuration
    $ mcloud config mysqapp --set-env prod    # set environment to prod
    $ mcloud config mysqapp --update          # reloads configuration
    $ mcloud config mysqapp --diff            # shows difference between current config and mcloud.yml file


.. note::

    Changes will be applied to the containers only after container rebuild.


.. warning::

    Mcloud will not remove the containers, if you remove them from config file.