mfcloud
======

mfcloud is a tool that orchestrates Docker containers localy and on
remote server.

Features:

- simple syntax mfcloud.yml, that describe containers you need for your application
- easily create application on remote deployment server
- easily push and pull volumes of Docker containers on remote server
- tcp balancer that knows which container serves which URL
- super-easy service discovery for applications

.. image:: docs/source/_static/mfcloud.png


Documentation
-------------

http://mfcloud.readthedocs.org/


Changelog
---------------------

0.4.4

stop, start, restart, rebuild, destroy commands now nderstand [service].[app] syntax,
allowing to restat single container. (Alex R.)

----------------------

0.4.3

Major improvments of container start order logic (Alex R.)

---------------------

