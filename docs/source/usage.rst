=================
Usage
=================


Basic commands
==================

List
----------

The most useful command of mcloud is list. It gives you an overview of status of your small cloud::

    $ mcloud list

    +------------------+------------------------------------+--------+-------------------------------------------------------------------------------------+
    | Application name |                Web                 | status |                                       services                                      |
    +------------------+------------------------------------+--------+-------------------------------------------------------------------------------------+
    |       ok1        |     ok1.mcloud.lh -> [No web]     |        |                                    web.ok1 (OFF)                                    |
    |                  | https://ok1.mcloud.lh -> [No web] |        |                                                                                     |
    +------------------+------------------------------------+--------+-------------------------------------------------------------------------------------+
    |       ok2        |     ok2.mcloud.lh -> [No web]     |        |                                    web.ok2 (OFF)                                    |
    |                  |    sok2.mcloud.lh -> [No web]     |        |                                                                                     |
    +------------------+------------------------------------+--------+-------------------------------------------------------------------------------------+
    |       mfcm       |    mfcm.mcloud.lh -> [No web]     |        |                                  elastic.mfcm (OFF)                                 |
    |                  |                                    |        |                                   mysql.mfcm (OFF)                                  |
    |                  |                                    |        |                                    php.mfcm (OFF)                                   |
    |                  |                                    |        |                                   nginx.mfcm (OFF)                                  |
    +------------------+------------------------------------+--------+-------------------------------------------------------------------------------------+
    |      1.test      |   1.test.mcloud.lh -> [No web]    |        |                               web.1.test (NOT CREATED)                              |
    |                  |                                    |        |                             another.1.test (NOT CREATED)                            |
    +------------------+------------------------------------+--------+-------------------------------------------------------------------------------------+

*list* command is command you will use many times a day, so it will be easier if you give it some short name::

    $ alias mf='mcloud list'

Then you can use it as::

    $ mf


Start, stop
--------------

You can start/stop applications::

    $ mcloud start ok1
    $ mcloud stop ok1
    $ mcloud restart ok1

*restart* executes *stop*, *start* sequentialy.

*stop* command will not remove your container and data inside.

Destroy, Rebuild
-------------------

Another useful command is *destroy*, and it's pairing command *redbuild*.

    $ mcloud destroy ok1
    $ mcloud rebuild ok1

NB! *destroy*  will remove your container with all the data inside, including volumes.

*restart* executes *destroy*, *start* sequentialy.


Debugging
================

It happens pretty often that application may not start inside mcloud.
Good news is that everything mcloud does with docker containers can be done by hands as well.

mcloud generates names for containers that are in formtat: [service].[application].
Container names are visible in right column when you execute *mcloud list* command.

If you know container name you can do a lot of things with it.

See logs of container::

    $ docker logs -f web.ok1


Restart single container::

    $ docker restart web.ok1

Inspect the container::

    $ docker inspect web.ok1

And many other things. Remeber, it's just a docker container!




