FROM continuumio/anaconda3

ENV MARKET_REPORTER_HOME_DIR "/opt/aistairc"
ENV MARKET_REPORTER_BASIC_AUTH_PASSWORD "market-reporter-basic-auth-password"

ENV DEBCONF_NOWARNINGS yes

RUN apt-get update && apt-get install -y \
    apache2-utils \
    gcc \
    g++ \
    make \
    nginx \
    postgresql-9.6 \
    sudo \
    supervisor \
    vim-tiny

RUN useradd --create-home --skel /etc/skel --home-dir ${MARKET_REPORTER_HOME_DIR} --shell /bin/bash reporter
RUN mkdir -p ${MARKET_REPORTER_HOME_DIR}/market-reporter \
    && chown reporter:reporter -R ${MARKET_REPORTER_HOME_DIR}/market-reporter

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
RUN echo $'[supervisord]\n\
user=root\n\
nodaemon=false\n\
\n\
[program:postgresql]\n\
user=postgres\n\
command=/usr/lib/postgresql/9.6/bin/postgres --config_file=/etc/postgresql/9.6/main/postgresql.conf\n\
\n\
[program:nginx]\n\
command=/usr/sbin/nginx -g "daemon off;"\n' > /etc/supervisor/conf.d/supervisord.conf
ENTRYPOINT /usr/bin/supervisord --nodaemon --user root --configuration /etc/supervisor/supervisord.conf

RUN openssl genrsa 2048 > nginx-selfsigned.key \
    && chmod 400 nginx-selfsigned.key \
    && openssl req -batch -new -key nginx-selfsigned.key > nginx-selfsigned.csr \
    && openssl x509 -in nginx-selfsigned.csr -days 30 -req -signkey nginx-selfsigned.key > nginx-selfsigned.crt \
    && mv nginx-selfsigned.crt /etc/ssl/certs/nginx-selfsigned.crt \
    && mv nginx-selfsigned.key /etc/ssl/private/nginx-selfsigned.key \
    && rm nginx-selfsigned.csr

RUN htpasswd -b -c /etc/nginx/.htpasswd reporter ${MARKET_REPORTER_BASIC_AUTH_PASSWORD}

USER postgres
RUN /etc/init.d/postgresql start \
    && createuser reporter\
    && createdb master reporter \
    && createdb test_db reporter \
    && /etc/init.d/postgresql stop

USER reporter
RUN echo "source /opt/conda/etc/profile.d/conda.sh" >> ${MARKET_REPORTER_HOME_DIR}/.bashrc \
    && echo "conda activate base" >> ${MARKET_REPORTER_HOME_DIR}/.bashrc
RUN git clone https://github.com/aistairc/market-reporter.git ${MARKET_REPORTER_HOME_DIR}/market-reporter

WORKDIR ${MARKET_REPORTER_HOME_DIR}/market-reporter
