FROM continuumio/anaconda3

ARG GITHUB_ACCESS_TOKEN
ARG BASIC_AUTH_PASSWORD
RUN test -n "$GITHUB_ACCESS_TOKEN" && test -n "$HTTP_PASSWARD"

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

RUN useradd --create-home --shell /bin/bash reporter
RUN mkdir -p /var/www/market-reporter \
    && chown reporter:reporter -R /var/www/market-reporter

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
ENTRYPOINT /usr/bin/supervisord --nodaemon --user root --configuration /etc/supervisor/supervisord.conf

RUN openssl genrsa 2048 > nginx-selfsigned.key \
    && chmod 400 nginx-selfsigned.key \
    && openssl req -batch -new -key nginx-selfsigned.key > nginx-selfsigned.csr \
    && openssl x509 -in nginx-selfsigned.csr -days 30 -req -signkey nginx-selfsigned.key > nginx-selfsigned.crt \
    && mv nginx-selfsigned.crt /etc/ssl/certs/nginx-selfsigned.crt \
    && mv nginx-selfsigned.key /etc/ssl/private/nginx-selfsigned.key \
    && rm nginx-selfsigned.csr    

RUN htpasswd -b -c /etc/nginx/.htpasswd reporter ${BASIC_AUTH_PASSWORD}

USER postgres
RUN /etc/init.d/postgresql start \
    && createuser reporter\
    && createdb master reporter \
    && createdb test_db reporter \
    && /etc/init.d/postgresql stop

USER reporter
RUN echo "source /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc \
    && echo "conda activate base" >> ~/.bashrc
RUN git clone https://${GITHUB_ACCESS_TOKEN}:x-oauth-basic@github.com/aistairc/market-reporter.git /var/www/market-reporter
