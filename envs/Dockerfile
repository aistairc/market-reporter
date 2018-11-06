FROM continuumio/anaconda3

ARG GITHUB_ACCESS_TOKEN
RUN test -n "$GITHUB_ACCESS_TOKEN"

ENV DEBCONF_NOWARNINGS yes

RUN apt-get update && apt-get install -y \
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
    && chown reporter:reporter -R market-reporter

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
ENTRYPOINT /usr/bin/supervisord --nodaemon --user root --configuration /etc/supervisor/supervisord.conf

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
