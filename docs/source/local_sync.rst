
======================
Synchronizing files
======================

Mcloud is armed with sync command that is super-useful for volumes syncronization.

local dir to remote volume
------------------------------

mcloud sync my_local_dir yyy.xxx@my_mcloud_server.com:/var/www


remote volume to local dir
-------------------------------

mcloud sync yyy.xxx@my_mcloud_server.com:/var/www my_local_dir

upload to remote application root volume (where mcloud.yml resides)
----------------------------------------------------------------------

mcloud sync my_local_dir xxx@my_mcloud_server.com


