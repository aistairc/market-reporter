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

RUN useradd --create-home --skel /etc/skel --home-dir ${HOME_DIR} --shell /bin/bash reporter
RUN mkdir -p ${HOME_DIR}/market-reporter \
    && chown reporter:reporter -R ${HOME_DIR}/market-reporter

COPY nginx.conf /etc/nginx/conf.d/nginx.conf
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
RUN echo "source /opt/conda/etc/profile.d/conda.sh" >> ${HOME_DIR}/.bashrc \
    && echo "conda activate base" >> ${HOME_DIR}/.bashrc
RUN git clone https://github.com/aistairc/market-reporter.git ${HOME_DIR}/market-reporter

WORKDIR ${HOME_DIR}/market-reporter
