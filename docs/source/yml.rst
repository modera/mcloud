
mfcloud.yml reference
==========================

Example::

    nginx:
        image: nginx

    memcache:
        image: jacksoncage/memcache

    app:
        build: local/dir
        volumes:
            local/dir/somedir: /var/data


First level key is service name. In example above we have
three services: nginx, memcache and app.


On second level one of image or build is required.

    image
        docker container will be build from docker image found in docker registry by name

    build
        docker container will be build from docker image build using command like:
        docker build local/dir

volumes is set of subdirectories that will be monted as subdirectories into docker container.
local relative path on left side, path inside container on right side.
