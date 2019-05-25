FROM continuumio/anaconda3:5.3.0

SHELL ["/bin/bash", "-c"]

ENV DEBCONF_NOWARNINGS yes

RUN apt-get update && apt-get install -y \
    apache2-utils \
    gcc \
    g++ \
    make \
    nginx \
    postgresql-client-9.6 \
    sudo \
    supervisor \
    vim-tiny

ENV MARKET_REPORTER_USER "reporter"

RUN useradd --create-home --skel /etc/skel \
    --home-dir /opt/${MARKET_REPORTER_USER} \
    --shell /bin/bash ${MARKET_REPORTER_USER}
RUN echo $'source /opt/conda/etc/profile.d/conda.sh\n\
conda activate base' >> /opt/${MARKET_REPORTER_USER}/.bashrc
RUN chown -R ${MARKET_REPORTER_USER}:${MARKET_REPORTER_USER} /opt/${MARKET_REPORTER_USER}

RUN echo $'server {\n\
    listen 443 ssl default_server;\n\
    charset utf-8;\n\
    client_max_body_size 80M;\n\
\n\
    ssl_certificate /etc/ssl/certs/nginx-selfsigned.crt;\n\
    ssl_certificate_key /etc/ssl/private/nginx-selfsigned.key;\n\
\n\
    location / {\n\
        auth_basic "Restricted";\n\
        auth_basic_user_file /etc/nginx/.htpasswd;\n\
        try_files $uri @webapp;\n\
    }\n\
\n\
    location @webapp {\n\
        include uwsgi_params;\n\
        uwsgi_pass unix:/opt/aistairc/market-reporter/uwsgi.sock;\n\
    }\n}' > /etc/nginx/conf.d/nginx.conf

RUN openssl genrsa 2048 > nginx-selfsigned.key \
    && chmod 400 nginx-selfsigned.key \
    && openssl req -batch -new -key nginx-selfsigned.key > nginx-selfsigned.csr \
    && openssl x509 -in nginx-selfsigned.csr -days 30 -req -signkey nginx-selfsigned.key > nginx-selfsigned.crt \
    && mv nginx-selfsigned.crt /etc/ssl/certs/nginx-selfsigned.crt \
    && mv nginx-selfsigned.key /etc/ssl/private/nginx-selfsigned.key \
    && rm nginx-selfsigned.csr

ENV MARKET_REPORTER_BASIC_AUTH_PASSWORD "market-reporter-basic-auth-password"

RUN htpasswd -b -c /etc/nginx/.htpasswd reporter ${MARKET_REPORTER_BASIC_AUTH_PASSWORD}

RUN echo $'[supervisord]\n\
user=root\n\
nodaemon=false\n\
\n\
[program:nginx]\n\
command=/usr/sbin/nginx -g "daemon off;"' > /etc/supervisor/conf.d/supervisord.conf

ENTRYPOINT /usr/bin/supervisord --nodaemon --user root --configuration /etc/supervisor/supervisord.conf

WORKDIR /opt/${MARKET_REPORTER_USER}
