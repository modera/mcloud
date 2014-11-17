
=======================================
Updating deployed application
=======================================

Updating applications is as easy as uploading changes::

    $ mcloud sync . flask-redis@<ip-here>

And restarting application::

    $ mcloud -h <ip-here> restart flask-redis

If you changed configuration in mcloud.yml, you may need to deploy changes to
container structure as well::

    $ mcloud -h <ip-here> config --update flask-redis

