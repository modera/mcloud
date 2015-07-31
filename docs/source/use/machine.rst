

Using docker-machine inside mcloud
------------------------------------

Mcloud has integrated docker-machine now and it's available as "machine" command.

Advantage over usual docker machine is that it's tightly integrated with mcloud deployments concept.
Whenever you create command through machiine, it's automatically picked up
by mcloud and available by application deployment.

Another thing is that mcloud machine is running inside mcloud-server, it means configs
are stored centrally on mcloud server.


Example::

    $ mcloud machine ls

    $ mcloud machine create -- --driver digitalocean test1

.. note::
    When using machine commands you need to insert "--". It's says that everything that goes after --
    should be passed directly to docker machine and this is not mcloud's options.

Reference for machine command is on docker site https://docs.docker.com/machine/#subcommands

To set environment variables like DIGITALOCEAN_ACCESS_TOKEN and others, you can use set command::

    $ mcloud set DIGITALOCEAN_ACCESS_TOKEN ffdksafjklsadjfkljsaklfja;kl

    $ mcloud vars

Those variables will be accessible to docker-machine on the given mcloud server.