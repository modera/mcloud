

Monitoring your deployments
============================================


Logs
--------------------

Obeserve logs of your container::

    mcloud logs myapp myservice


Run
-------------------------

Hack inside your container::

    mcloud run myapp myservice


.. note::
    "run" command creates exact copy of containers and mount same volumes.
    **Only changes** made to volumes will affect your original container.

