
========
ficloud
========

ficloud alows to deploy your fig infrastructure to remote servers. Also it provides all the services needed for hosting production apps.

NB! ficloud is currently in development stage.


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
You can use pip to install ficloud quickly and easily::

    $ pip install ficloud

Need more help with installing? See installation.


User's Guide
============

.. toctree::
   :maxdepth: 2

   installation
   quickstart

Contribute
==========
Found a bug in or want a feature added to ficloud?
You can fork the official https://github.com/pywizard/ficloud or file an issue ticket
on github. You can also ask questions at the official
ficloud-project@googlegroups.com or directli in google-group https://groups.google.com/forum/#!forum/ficloud-project.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
