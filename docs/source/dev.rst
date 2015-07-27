

Developing mcloud
-----------------------

Easiest way to develop mcloud is to mount volume that contains mcloud source into the container::

MacOS::

    docker run -d -v /Users:/Users -v /var/run/docker.sock:/var/run/docker.sock -v /Users/alex/dev/mcloud/mcloud:/opt/mcloud/local/lib/python2.7/site-packages/mcloud  --name mcloud mcloud/mcloud

Linux::

    docker run -d -v /home:/home -v /var/run/docker.sock:/var/run/docker.sock -v /home/alex/dev/mcloud/mcloud:/opt/mcloud/local/lib/python2.7/site-packages/mcloud  --name mcloud mcloud/mcloud


This way you can edit mcloud source and see results.

You also may create client containser and execute mcloud client from there::

    $ docker run -i -t --volumes-from mcloud --link mcloud --rm -w `pwd` mcloud/mcloud bash

    $ mcloud list

Another usefull trick is to execute mcloud-server manualy and install mcloud manually::

    # create container
    $ docker run -d -v /Users:/Users -v /var/run/docker.sock:/var/run/docker.sock -v /Users/alex/dev/mcloud:/opt/mcloud-src --name mcloud mcloud/mcloud
    $ /opt/mcloud/bin/pip install -e /opt/mcloud-src

    # attach to container
    $ docker exec -i -t mcloud bash

    # inside continer:
    $ supervisorctl stop mcloud
    $ mcloud-server


Generating new version
--------------------------

