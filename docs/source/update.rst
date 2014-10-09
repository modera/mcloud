



Updating mflcoud
============================================

Update is easy::

    $ sudo /opt/mfcloud/bin/pip install -U mfcloud

And restart service::

    $ sudo service mfcloud restart

Uninstalling mflcoud
============================================

- Remove upstart/supervisor script
- If, you used mfcloud with supervisor, you may need to uninstall supervisor as well
- Remove mfcloud commands: sudo rm /usr/local/bin/mfcloud*
- Remove mfcloud home: sudo rm -rf /opt/mfcloud
- Remove mflcoud-dns
