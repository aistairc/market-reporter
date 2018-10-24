FROM continuumio/anaconda3

RUN apt-get update && apt-get install -y \
    emacs \
    gcc \
    g++ \
    nginx \
    postgresql-9.6 \
    sudo \
    supervisor \
    vim

RUN useradd --create-home --shell /bin/bash plu

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

USER postgres

RUN /etc/init.d/postgresql start \
    && createuser plu \
    && createdb master plu \
    && /etc/init.d/postgresql stop

USER plu

RUN echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc \
    && echo "conda activate base" >> ~/.bashrc

WORKDIR /home/plu/

COPY startup.sh .

ARG GITHUB_ACCESS_TOKEN
RUN git clone https://${GITHUB_ACCESS_TOKEN}:x-oauth-basic@github.com/aistairc/market-reporter.git

USER root

CMD ["./startup.sh"]