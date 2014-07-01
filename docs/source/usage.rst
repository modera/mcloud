
How to
=================

.. note::

    It will be super-useful if you are familiar with basic concepts of docker. You can find lot's of tutorials and very
    descriptive documentation on http://docker.io website.


Let's assume our example application uses the following application configuration:

.. image:: _static/mfcloud_simpleapp.png


mfcloud runs every service in separate docker container. For this application
we need four:

- php-fpm itself
- mysql
- memcache
- nginx

