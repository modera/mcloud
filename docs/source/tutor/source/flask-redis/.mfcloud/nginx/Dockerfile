
FROM orchardup/nginx

VOLUME /var/www

RUN rm /etc/nginx/sites-available/default
ADD nginx.conf /etc/nginx/sites-available/default

WORKDIR /var/www

CMD nginx