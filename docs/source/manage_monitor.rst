

Monitoring your deployments
============================================


Logs
--------------------

Obeserve logs of your container::

    mfcloud logs myapp myservice


Run
-------------------------

Hack inside your container::

    mfcloud run myapp myservice


.. note::
    "run" command creates exact copy of containers and mount same volumes.
    **Only changes** made to volumes will affect your original container.

