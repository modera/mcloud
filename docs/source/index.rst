
==============
Welcome
==============

Welcome to *ModeraCloud* - a tool that helps you manage Docker based deployments.

- Describe deployment in a simple configuration file.
- Keep the configuration in a VCS with your application code.
- Use command-line tool to manage the containers locally and remotely.

Getting started
--------------------

See installation chapter for details.

.. uml::

    @startuml

    start

    if (multiprocessor?) then (yes)
      fork
        :Treatment 1;
      fork again
        :Treatment 2;
      end fork
    else (monoproc)
      :Treatment 1;
      :Treatment 2;
    endif

    @enduml

Contents
------------------

.. toctree::
  :maxdepth: 2

  start
  local
  remote
  manage
  api
