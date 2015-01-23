
======================
Backup volumes
======================

mcloud backup command allows to backup files to amazon s3:// service


Example::

    $ mcloud backup mysql.timber /var/lib/mysql s3://mcloud-backups/timber_test/

    $ mcloud restore mysql.timber /var/lib/mysql s3://mcloud-backups/timber_test/

