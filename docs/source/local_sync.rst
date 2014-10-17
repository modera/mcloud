
======================
Synchronizing files
======================

mfcloud is able now feature-complete, so ssh-access to s3 server will be revoked from everybody (except responsible persons Alex, Stas, Sergei V.)

Now you can see logs and login into container remotely.

Instead of:
ssh admin1@s3.cloud.modera.org && docker run yyy.xxx

write this (on local machine):

mfcloud -h s3.cloud.modera.org run yyy.xxx

Also mfcloud logs are working:

mfcloud -h s3.cloud.modera.org logs yyy.xxx

It will be equal to:
ssh admin1@s3.cloud.modera.org && docker logs -f --tail=100 yyy.xxx


New version of mfcloud also us own file transfer protocol, that does not require Rsync & ssh.

Usage example:

1) local dir to remote volume
mfcloud sync my_local_dir yyy.xxx@s3.cloud.modera.org:/var/www


2) remote volume to local dir
mfcloud sync yyy.xxx@s3.cloud.modera.org:/var/www my_local_dir

3) remote to remote
mfcloud sync yyy.xxx@s3.cloud.modera.org:/var/www yyy.zzz@s3.cloud.modera.org:/var/www

4) local to local (sync two dirs)

mfcloud sync some/dir another/dir

5) upload to remote application root volume (where mfcloud.yml resides):

mfcloud sync my_local_dir xxx@s3.cloud.modera.org
[13:35.15] Aleksandr Rudakov: > [neljapäev, 25. september 2014 13:34.34 [djinni.co] Michael] [djinni.co] Michael: Can i update mfcloud apps on dev-server?


