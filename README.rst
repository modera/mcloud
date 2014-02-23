ficloud
======

ficloud alows to deploy your fig infrastructure to remote servers. Also it
provides all the services needed for hosting production apps.

NB! ficloud is currently in concept stage, so documentation for future components is only thing that exist now.

Features:

 - define your app config through Dockerfile and fig.yml
 - easy deploy through git push
 - pushing several versions of app (dev, staging, production ... etc)
 - simple nginx based balancer
 - easy switch balancer endpoint between app versions (ex swap prod and dev)
 - persistent storage for containers
 - easy copying persistence storage between containers (prod -> staging, etc)
 - ftp access for container persistence storage

Tutorial
----------

Nb! there is no code that implements things described in tutorial yet.

Set working ssh account::

    $ ficloud use ubuntu@myserver.com

Apps:

    $ ficloud app create myapp
    $ ficloud app list
    $ ficloud app remove

push code::

    $ git push ubuntu@myserver.com:myapp master:staging

Install balancer::

    $ ficloud-server balancer install
    $ ficloud-server balancer uninstall

    $ ficloud-server balancer set mydomain.com myapp@localhost/staging/web:5000
    $ ficloud-server balancer remove mydomain.com




