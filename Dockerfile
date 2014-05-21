
FROM ribozz/pywizard

RUN apt-get update
RUN apt-get upgrade -y

RUN apt-get install -y cron php5-fpm php5-mysql php-apc php5-imagick php5-imap php5-mcrypt php5-curl php5-gd php5-idn php-pear php5-json php5-memcache php5-mhash php5-ming php5-ps php5-pspell php5-recode php5-snmp php5-sqlite php5-tidy php5-xmlrpc php5-xsl

RUN apt-get install -y nginx

# Install Oracle Java 7
#RUN apt-get -y install python-software-properties
#RUN add-apt-repository ppa:webupd8team/java
#RUN apt-get -y update
#RUN echo "oracle-java7-installer  shared/accepted-oracle-license-v1-1 boolean true" | debconf-set-selections
#RUN apt-get -y install oracle-java7-installer


RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin
RUN mv /usr/local/bin/composer.phar /usr/local/bin/composer

RUN sed -i -e"s/;cgi.fix_pathinfo=1/cgi.fix_pathinfo=0/g" /etc/php5/fpm/php.ini
RUN sed -i -e"s/;daemonize\s*=\s*yes/daemonize = no/g" /etc/php5/fpm/php-fpm.conf
RUN find /etc/php5/cli/conf.d/ -name "*.ini" -exec sed -i -re"s/^(\s*)#(.*)/\1;\2/g" {} \;
#RUN sed -i -re"s/^\s*(user|group)\s*=.*$/\1 = www-data/" /etc/php5/fpm/pool.d/www.conf
RUN sed -i -re"s/^listen\s*=\s*\/var\/run\/php5-fpm.sock.*/listen = 9000/" /etc/php5/fpm/pool.d/www.conf
#RUN sed -i -re"s/^.*;listen\.(owner|group)\s*=\s*www-data.*$/listen\.\1 = php-user/" /etc/php5/fpm/pool.d/www.conf
RUN sed -i -e"s/;date.timezone =/date.timezone = Europe\/Tallinn/g" /etc/php5/fpm/php.ini
RUN sed -i -e"s/;date.timezone =/date.timezone = Europe\/Tallinn/g" /etc/php5/cli/php.ini

# allow ssh access
#RUN  echo "    IdentityFile /.ssh/id_rsa" >> /etc/ssh/ssh_config
#ADD id_rsa /.ssh/id_rsa
#RUN chmod go-rwx -R /.ssh


# Install Supervisor.
RUN \
  apt-get install -y supervisor && \
  sed -i 's/^\(\[supervisord\]\)$/\1\nnodaemon=true/' /etc/supervisor/supervisord.conf

# install python
RUN apt-get install -y python python-dev python-pip libssl-dev build-essential libffi-dev
RUN pip install virtualenv


ADD . /var/www
ADD .docker/nginx.conf /etc/nginx/sites-enabled/default

RUN echo "\ndaemon off;" >> /etc/nginx/nginx.conf


RUN apt-get install -y mysql-server-5.5
ADD .docker/my.cnf /etc/mysql/conf.d/my.cnf
RUN chmod 664 /etc/mysql/conf.d/my.cnf
ADD .docker/mysql.sh /usr/local/bin/mysqlrun
RUN chmod +x /usr/local/bin/mysqlrun

VOLUME ["/var/lib/mysql"]

EXPOSE 3306

RUN ln -s /var/www/

RUN virtualenv /var/env
RUN /var/env/bin/pip install -r /var/www/websocket/requirements.txt

VOLUME ["/var/www", "/etc/supervisor/conf.d"]

CMD ["supervisord", "-c", "/var/www/.docker/supervisord.conf"]


