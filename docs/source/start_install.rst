
============================================
Installation
============================================


docker run -i -t --rm -v /Users:/Users -v /var/run/docker.sock:/var/run/docker.sock -v /Users/alex/dev/mcloud/mcloud:/opt/mcloud/local/lib/python2.7/site-packages/mcloud -p 7080:7080 --name mcloud mcloud/mcloud

docker run -i -t --volumes-from mcloud --link mcloud --rm -w `pwd` mcloud mcloud

linux:

-v /var/run/docker.sock:/var/run/docker.sock

ModeraCloud uses Docker as the core component to host the services. Therefore, the first question to be answered is whether you want to install and run everything:

#. straight on the machine, or
#. inside a virtual environment

If you are not on Linux then as of today you don't really have any options other than running it inside the virtual machine. Here are all 4 different ways to help you on board:

**Easy & automated** - recommended for local and development machines:

.. toctree::
  :maxdepth: 1

  start_install_linux
  start_install_other

**Manual & flexible** - recommended for remote and production machines:

.. toctree::
  :maxdepth: 1

  start_install_advanced
  start_install_from_source
