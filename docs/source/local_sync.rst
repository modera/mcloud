
======================
Synchronizing files
======================

Mcloud is armed with sync command that is super-useful for volumes syncronization.

local dir to remote volume
------------------------------

mfcloud sync my_local_dir yyy.xxx@my_mcloud_server.com:/var/www


remote volume to local dir
-------------------------------

mfcloud sync yyy.xxx@my_mcloud_server.com:/var/www my_local_dir

remote to remote
-------------------------------

mfcloud sync yyy.xxx@my_mcloud_server.com:/var/www yyy.zzz@my_mcloud_server.com:/var/www

local to local (sync two dirs)
-------------------------------

mfcloud sync some/dir another/dir

upload to remote application root volume (where mcloud.yml resides)
----------------------------------------------------------------------

mfcloud sync my_local_dir xxx@my_mcloud_server.com


