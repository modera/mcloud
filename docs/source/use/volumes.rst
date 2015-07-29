
Volume synchronization
===========================

Volume commands are about controlling the service volumes and data synchronization.


Syntax
-----------

Synchronize volumes and folders. Syntax is::

    $ mcloud {from} {to} [--no-remove] [--force]

From and to are volume spec.
Spec for remote volume::

    [service.]app@host[:/volume/path]

host may be set to "@me" which is current host.
service and volume name may be skipped, then command assumes it's main volume of application (where mcloud.yml resides)

If volume spec do not match remote volume format, then command assumes, it is
just directory name.


Work order
--------------

#. Command computes snapshot of source and destination locations by collecting list of files,
   calculating modification time diffs. (time diff = server current time - modification time)
#. Compares result, and if no --force flag, shows diff list to user. (new, updated, removed files)
#. if no --force flag, ask confirmation from user
#. Create archive with new and updated files
#. Transfer archive (progress is displayed)
#. Extract archive
#. if no --no-remove flag, removes files.


Usage patterns
----------------

- local folder to local folder
- remote volume to local folder
- local folder to remote volume
- remote volume to remote volume

