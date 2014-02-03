ficloud
======

ficloud alows to deploy your fig infrastructure to remote servers. Also it
provides all the services needed for hosting production apps.

NB! ficloud is currently in concept stage, so documentation for future components is only thing that exist now.

Features:

 - define your app config through Dockerfile and fig.yml
 - easy deploy through git push
 - pushing several versions of app (dev, staging, prod ... etc)
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

Branches::

    $ ficloud branch list myapp
    $ ficloud branch remove myapp version

push code::

    $ git push ubuntu@myserver.com:myapp master:staging

Install balancer::

    $ ficloud balancer install
    $ ficloud balancer uninstall

    $ ficloud balancer set mydomain.com myapp@localhost/staging/web:5000
    $ ficloud balancer remove mydomain.com

Working with storage::

    $ ficloud storage copy myapp@/staging/web/mysql myapp@/prod/web/mysql




