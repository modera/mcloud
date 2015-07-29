
=====================================
Protecting Mcloud with SSL
=====================================


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

    sudo service mcloud restart

Local machine
************************


Put certificates files into ~/.mcloud/:

- my_server.crt
- my_server.key

Instead of "my_server" put your hostname you use to connect to mcloud.

Now `mcloud` command will autodetect and use your certificates.

