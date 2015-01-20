
=======================================
Server backup to s3
=======================================

.. note::

    Backup commands available only starting from latest versions of mcloud.

Make sure you have installed and configured aws-cli tool and configure it.
root user on target machine should have access to this tool

http://aws.amazon.com/cli/

Then you can use it as follows::

    $ mcloud backup service.app@myhost.com s3://some-bucket/

    ... a lot of aws output

    Backup id: 76ffaefhhh980329

And restore:

    $ mcloud backup service.app@myhost.com s3://some-bucket/ --restore 76ffaefhhh980329


