
==============
Modera Cloud
==============

Modera Cloud is set of tools that use Docker containers to deploy web-applications to production.

Features
------------------------------------------

 * Configure and test your environment locally (php, mysql, elasticsearch, nodejs, java... anything*)
 * Push to cloud in couple commands
 * Live server updates with no downtime
 * Easy data migration between application versions and dev/staging/live environments
 * Fast rollbacks, easy backups


User's Guide
============

.. toctree::
   :maxdepth: 2




.. uml::
    :width: 300mm

    @startuml





    package "Modera Cloud Manager" {

      HTTP - [Modera Application]

      [Modera Application] ..> [websocket server]

      [websocket server] ..> RPC1
      [websocket server] ..> ZeroMQ1
      [websocket server] ..> RPC2
      [websocket server] ..> ZeroMQ2
    }



    folder "Deployment server 1" {

        RPC1 - [mfcloud1]
        ZeroMQ1 - [mfcloud1]

        [mfcloud1] ..> DockerAPI1 : use
        interface "DockerAPI1 (HTTP)" as DockerAPI1

        [mfcloud1] -> [internal DNS 1]

        [nginx.v1.2.3.myapp]
        [php.v1.2.3.myapp]
        [nginx.v1.2.4.myapp]
        [php.v1.2.4.myapp]
    }

    folder "Deployment server 2" {

        RPC2 - [mfcloud2]
        ZeroMQ2 - [mfcloud2]

        [mfcloud2] ..> DockerAPI2 : use
        interface "DockerAPI2 (HTTP)" as DockerAPI2

        [mfcloud2] -> [internal DNS 2]

        [nginx.v1.2.3.otherapp]
        [php.v1.2.3.otherapp]
    }

   @enduml



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
