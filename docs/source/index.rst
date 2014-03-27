
========
mfcloud
========

mfcloud alows to deploy your fig infrastructure to remote servers. Also it provides all the services needed for hosting production apps.

NB! mfcloud is currently in development stage.


Deploy your fig-docker environment easily
------------------------------------------

 * define your app config through Dockerfile and fig.yml
 * easy deploy through git push
 * pushing several versions of app (dev, staging, prod ... etc)
 * simple nginx based balancer
 * easy switch balancer endpoint between app versions (ex swap prod and dev)
 * persistent storage for containers
 * easy copying persistence storage between containers (prod -> staging, etc)
 * ftp access for container persistence storage

Get started quickly with a simple example in quickstart.

Easy installation
-----------------


.. raw:: html

    <div style="margin-left: -53px; margin-right: -80px;">
        <script type="text/javascript" src="https://asciinema.org/a/14.js" id="asciicast-14" async></script>
    </div>


User's Guide
============

.. toctree::
   :maxdepth: 2

   installation
   server
   deploy


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
