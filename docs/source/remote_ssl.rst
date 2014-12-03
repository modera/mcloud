
=====================================
Using SSL with MCloud applications
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

Restart mcloud server::

    sudo service mcloud restart

Local machine
************************


Put certificates files into ~/.mcloud/:

- 127.0.0.1.crt
- 127.0.0.1.key

Instead of 127.0.0.1 put your hostname you use to connect to mcloud.

Now `mcloud` command will autodetect and use your certificates.

