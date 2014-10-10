
===============================================
Sample Nginx+PHP+MySQL deployment
===============================================

In this example we will deploy Symfony application.

Checkout repo::

    $ git clone https://github.com/cravler/mfcloud-symfony.git

Start mfcloud and init application::

    $ mfcloud

    mcloud: ~@me>  init symfony

    mcloud: ~@me>

Start the application::

    mcloud: ~@me>  use symfony

    mcloud: symfony@me>  start


    .... lots of output from build process ...


Status::

    mcloud: symfony@me>  status

    +-----------------+--------+------------+-------+--------+----------------+---------------------+
    |   Service name  | status |     ip     | cpu % | memory |    volumes     | public urls         |
    +-----------------+--------+------------+-------+--------+----------------+---------------------+
    |  mysql.symfony  |   ON   | 172.17.0.3 | 0.32% |  572M  |  /etc/my.cnf   |                     |
    |                 |        |            |       |        | /var/lib/mysql |                     |
    +-----------------+--------+------------+-------+--------+----------------+---------------------+
    | postfix.symfony |   ON   | 172.17.0.4 | 0.13% |  33M   |                |                     |
    +-----------------+--------+------------+-------+--------+----------------+---------------------+
    |   php.symfony   |   ON   | 172.17.0.5 | 0.00% |   5M   |    /var/www    |                     |
    |                 |        |            |       |        |   /.composer   |                     |
    +-----------------+--------+------------+-------+--------+----------------+---------------------+
    |  nginx.symfony  |   ON   | 172.17.0.6 | 1.00% |   2M   |    /var/www    | symfony.mflcoud.lh  |
    +-----------------+--------+------------+-------+--------+----------------+---------------------+


Now it running.
