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

Configure your project to run with fig.yml::

    $ figaro use ubuntu@myserver.com
    $ figaro init myapp

That is equivalent to::

    $ ssh ubuntu@myserver.com

ubuntu$ git init --bare myapp

now push code::

    $ git push ubuntu@myserver.com:myapp staging

rewiev deployed app versions::

    $ figaro apps

    myapp:
    - staging

    $ figaro balancer

no balancer installed on ubuntu@myserver.com::

    $ figaro balancer install

    $ figaro balancer mydomain.com myapp@localhost/staging/web:5000
    $ figaro balancer mydomain.com disable

Working with storage::

    $ figaro storage copy myapp@localhost/staging/web/mysql myapp@localhost/prod/web/mysql
    $ figaro storage snapshot myapp@localhost/staging/web/mysql s3://some/bucket#v1.2.3
    $ figaro storage restore s3://some/bucket#v1.2.3 myapp@localhost/staging/web/mysql




