

Developing mcloud
-----------------------

Easiest way to develop mcloud is to mount volume that contains mcloud source into the container::

MacOS::

    docker run -d -v /Users:/Users -v /var/run/docker.sock:/var/run/docker.sock -v /Users/alex/dev/mcloud/mcloud:/opt/mcloud/local/lib/python2.7/site-packages/mcloud  --name mcloud mcloud/mcloud

Linux::

    docker run -d -v /home:/home -v /var/run/docker.sock:/var/run/docker.sock-v /home/alex/dev/mcloud/mcloud:/opt/mcloud/local/lib/python2.7/site-packages/mcloud  --name mcloud mcloud/mcloud