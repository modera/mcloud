
=================================
Production mcloud deployment
=================================


Install production Mcloud Server
-----------------------------------

Installation of production server is even easier than local deployment istallation.

Command for production server you need linux os with docker installed. Some
cloud providers already have images with such config.


Spin up the container::

    $ docker run -d --restart always -v /etc/mcloud:/etc/mcloud -v /root:/root -v /var/run/docker.sock:/var/run/docker.sock -p 7080:7080 --name mcloud mcloud/mcloud

Haprxoy is also needed::

    $ docker exec -it mcloud mcloud-plugins install mcloud-plugin-haproxy

Major diference from local installation is that we mount /root directory instead of home, /etc/mcloud directoy and we also expose 7080 port.

/root directory stores all application files, so it's always good idea to have direct access to this.
/etc/mcloud is place where we can create mcloud-server.yml config.

.. note::

Protecting Mcloud with SSL
--------------------------------


As an authentication method, mcloud use SSL.
For both client and server you will need to create and sign certificates.

Easies way to do this is to use XCA tool: http://sourceforge.net/projects/xca/

Remote machine configuration
*******************************

Create /etc/mcloud/mcloud-server.yml::

    ssl:
        enabled: true

On your remote machine.

And put three files into /etc/mcloud:

- ca.crt
- server.crt
- server.key

Put correct privileges to files::

    sudo chmod go-rwx -R /etc/mcloud

Restart mcloud server::

    docker restart mcloud

Local machine
************************


Put certificates files into ~/.mcloud/:

- my_server.crt
- my_server.key

Instead of "my_server" put your hostname you use to connect to mcloud.

Now `mcloud` command will autodetect and use your certificates.


Testing connection to server
--------------------------------------------

::

    $ mcloud --host myserver_hostname_or_ip list

Command should show empty application list.





