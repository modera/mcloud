
FROM ubuntu

RUN apt-get update && apt-get install -y redis-server supervisor build-essential python-dev python-pip

ADD . /locator

RUN pip install -r /locator/requirements.txt

ADD supervisor.conf /etc/supervisor/conf.d/supervisord.conf


EXPOSE 53/udp 53 6379

CMD ["/usr/bin/supervisord"]
