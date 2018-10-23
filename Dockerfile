FROM continuumio/anaconda3

RUN apt-get update && apt-get install -y \
    emacs \
    gcc \
    g++ \
    nginx \
    openssh-server \
    postgresql \    
    sudo \
    supervisor \
    vim

RUN useradd --create-home --shell /bin/bash plu

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# EXPOSE 22 5432

USER postgres
CMD supervisord -c /etc/supervisor/supervisord.conf

RUN /etc/init.d/postgresql start \
    && createuser plu \
    && createdb master plu

USER plu

RUN echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc \
    && echo "conda activate base" >> ~/.bashrc

WORKDIR /home/plu/

ARG GITHUB_ACCESS_TOKEN
RUN git clone https://${GITHUB_ACCESS_TOKEN}:x-oauth-basic@github.com/aistairc/market-reporter.git