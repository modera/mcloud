figaro
======

Figaro alows to deploy your fig infrastructure to remote servers. Also it
provides all the services needed for hosting production apps.

NB! Figaro is currently in concept stage, so documentation for future components is only thing that exist now.

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

    $ figaro use ubuntu@myserver.com

Apps:

    $ figaro app create myapp
    $ figaro app list
    $ figaro app remove

Branches::

    $ figaro branch list myapp
    $ figaro branch remove myapp version

push code::

    $ git push ubuntu@myserver.com:myapp master:staging

Install balancer::

    $ figaro balancer install
    $ figaro balancer uninstall

    $ figaro balancer set mydomain.com myapp@localhost/staging/web:5000
    $ figaro balancer remove mydomain.com

Working with storage::

    $ figaro storage copy myapp@/staging/web/mysql myapp@/prod/web/mysql




