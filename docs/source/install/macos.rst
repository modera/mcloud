

Preparing Mac Os for mfcloud
==================================

Install virtualbox (or any other virtualization of your choice).

Install ubuntu on virtual machine.

Then mount your directory with dev-projects into virtual machine using NFS.

NFS directories
********************

Here is one easy manual how to mount folders in MacOS using NFS:
http://technology.trapeze.com/journal/working-files-ubuntu-virtual-machine-your-mac/

DNS Configuration
********************

Install homebrew: http://brew.sh

Install dnsmasq::

    $ brew update
    $ brew install dnsmasq

Configure dnsmasq. You can copy default config file::

    $ cp /usr/local/opt/dnsmasq/dnsmasq.conf.example /usr/local/etc/dnsmasq.conf

where «/usr/local» is default brew folder (obtained by bred —prefix command)
or you can simply create empty conf file: /usr/local/etc/dnsmasq.conf

Add to the end of conf file next::

    address=/mfcloud.lh/<VM ip address>

Copy dnsmasq to launch daemons::

    $ sudo cp -fv /usr/local/opt/dnsmasq/*.plist /Library/LaunchDaemons

Route all *mfcloud.lh addresses to local name server::

    $ mkdir /etc/resolver *if required*
    $ echo 'nameserver 127.0.0.1' > /etc/resolver/mfcloud.lh

Launch it:

    $ sudo launchctl load /Library/LaunchDaemons/homebrew.mxcl.dnsmasq.plist

To restart just kill all processes of dnsmasq::

    $ sudo kill $(ps aux | grep '[d]nsmasq' | awk '{print $2}')

