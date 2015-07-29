

=======================================
"Zero" down-time updates with publish
=======================================

Simple version of zero down-time scenario may be achived by deploying
two versions of applications, and publishing only one in time.

.. note::
    This is not really zero-downtime, "it's minimal possible downtime"

Deploy initial version
========================

Create two tenants::

    $ mcloud -h <ip-here> init tenantA_flask-redis mcloud.yml
    $ mcloud -h <ip-here> init tenantB_flask-redis mcloud.yml

    ... do usual deploy here

Now publish tenant A::

    $ mcloud -h <ip-here> publish tenantA_flask-redis my-domain.com


Deploy & test
========================

Deploy new code & structure to tenant B

    $ mcloud sync . tenantB_flask-redis@<ip-here>
    $ mcloud -h <ip-here> restart tenantB_flask-redis
    $ mcloud -h <ip-here> config --update tenantB_flask-redis

Copy data from live server::

    $ mcloud sync tenantA_flask-redis@<ip-here> tenantB_flask-redis@<ip-here>

Now publish tenant B, so testers can test through the changes::

    $ mcloud -h <ip-here> publish tenantB_flask-redis testing.my-domain.com


Publish changes
========================

This steps should be done quickly, then for you customers it will look like as
several seconds hang-up::

    $ mcloud -h <ip-here> pause tenantA_flask-redis
    $ mcloud sync --force tenantA_flask-redis@<ip-here> tenantB_flask-redis@<ip-here>
    $ mcloud -h <ip-here> publish tenantB_flask-redis my-domain.com

Rollback
========================

If happens you still have some terrible bug on tenant B, that was not discovered during testing session,
you can rollback easily::

    $ mcloud -h <ip-here> publish tenantA_flask-redis my-domain.com
    $ mcloud -h <ip-here> resume tenantA_flask-redis

On success
========================

If update went well, you can resume tenant A, so next time this server will get updated::

    $ mcloud -h <ip-here> resume tenantA_flask-redis


Next update
========================

On next update scenario is same, except you will deploy new version to tenant A, and then swap with
tenant B, that is in production.