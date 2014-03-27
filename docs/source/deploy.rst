

Deploy application
======================

Start by creating application that is working locally using fig.yml

Set working ssh account::

    $ mfcloud use mfcloud@myserver.com

Create an application:

    $ mfcloud remote app-create foo

Deploy code:

    $ git push mfcloud@myserver.com:apps/foo master:prod

Check port number:

    $ mfcloud remote app-list

Configure balancer:

    $ mfcloud remote balancer set mydomain.com web:80@foo#prod

Push volume to deployment:

    $ filcoud volume-push web/code@foo#master

Push volume from deployment:

    $ filcoud volume-pull web/code@foo#master

Remote volume copy:

    $ mfcloud remote volume-copy web/code@foo#master foo#v1

Your app is deployed!
