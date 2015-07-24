

Types of mcloud deployments
-----------------------------

Mcloud has server and client parts:

.. uml::

    @startuml

    [Mcloud client] as cli
    [Mcloud server] as srv

    cli .right.> srv : WebsocketAPI


    srv .down.> [Docker1] : RemoteAPI
    srv .down.> [Docker2] : RemoteAPI
    srv .down.> [Docker3] : RemoteAPI


    @enduml


And there is several ways to install mcloud.


Docker & mcloud server on local machine
=========================================

.. uml::

    @startuml

    node "Local machine" {

        [Docker Server] as docker

        node "Mcloud container" {
            [Mcloud-Server] as srv

            [Mcloud-client] -left-> srv

            srv .left.> docker : use
        }

        node "container 1" as c1
        node "container 2" as c2
        node "container ..." as c3
        node "container N" as c4

        docker -down-> c1
        docker -down-> c2
        docker -down-> c3
        docker -down-> c4

        folder "Host Filesystem" {
            [/home] as home
        }

        srv -> home : mount

    }

    @enduml


Mcloud server on remote machine
=========================================

.. uml::

    @startuml

    node "Remote machine" {

        [Docker Server] as docker

        node "Mcloud container remote" {
            [Mcloud-Server] as srv

            srv .right.> docker : use
        }

        node "container 1" as c1
        node "container 2" as c2
        node "container ..." as c3
        node "container N" as c4

        docker -down-> c1
        docker -down-> c2
        docker -down-> c3
        docker -down-> c4

        folder "Remote Filesystem" {
            [/some-dir] as rdir
        }

        node "rsync container" {
            [rsync]
        }

        rsync -up-> rdir : mount

        srv -right-> rdir : mount
    }

    node "Local machine" {

        [Docker Server] as dockerl

        node "Mcloud container local" {
            [Mcloud-client] as cli
            cli -left-> srv
        }

        folder "Host Filesystem" {
            [/home] as home
        }

        cli -right-> home : mount

        home .right.-> rsync : mcloud file sync
    }


    @enduml