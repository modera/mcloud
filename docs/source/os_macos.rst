

Usage on macos
==========================

mcloud start
Using folder name as application name: myapp

[14] Starting application
[14] Got response
[14] Service mysql.myapp is not created. Creating

Pulling repository mysql{
    u'error': u'Get https://index.docker.io/v1/repositories/library/mysql/images: dial tcp: lookup index.docker.io on 192.168.0.1:53: read udp 192.168.0.1:53: i/o timeout',
    u'errorDetail': {
        u'message': u'Get https://index.docker.io/v1/repositories/library/mysql/images: dial tcp: lookup index.docker.io on 192.168.0.1:53: read udp 192.168.0.1:53: i/o timeout',
    },
}

  <class 'mcloud.remote.TaskFailure'>: [<twisted.python.failure.Failure <class 'mcloud.txdocker.CommandFailed'>>, <twisted.python.failure.Failure <class 'twisted.web.http._DataLoss'>>]


$ docker pull mysql

Pulling repository mysql
FATA[0025] Get https://index.docker.io/v1/repositories/library/mysql/images: dial tcp: lookup index.docker.io on 192.168.0.1:53: read udp 192.168.0.1:53: i/o timeout

https://github.com/kitematic/kitematic/issues/592

docker-machine ssh dev
echo "nameserver 8.8.8.8" > /etc/resolv.conf


Ping google.com
--------------------

Restart kitematic if there is no internet connection

Development on macos
===============================

docker run -d -v /opt/mcloud/local/lib/python2.7/site-packages/mcloud:/Users/alex/dev/mcloud/mcloud -v /Users:/Users --name mcloud mcloud/mcloud-osx

https://cryptography.io/en/latest/installation/#using-your-own-openssl-on-os-x

$ brew install openssl
$ env ARCHFLAGS="-arch x86_64" LDFLAGS="-L/usr/local/opt/openssl/lib" CFLAGS="-I/usr/local/opt/openssl/include" pip install cryptography

brew install pkg-config libffi
PKG_CONFIG_PATH=/usr/local/opt/libffi/lib/pkgconfig pip install cffi

Other dependencies are installed as they are.
