FROM postgres:10.5

ENV DEBCONF_NOWARNINGS yes
ENV PATH /opt/anaconda/bin:$PATH

RUN apt-get update && apt-get -y install \
    git \
    nginx \
    wget

# Anaconda
RUN mkdir /opt && \
    wget --quiet https://repo.anaconda.com/archive/Anaconda3-5.3.0-Linux-x86_64.sh -O /opt/anaconda.sh && \
    groupadd anaconda && \
    useradd --system --gid anaconda anaconda

USER anaconda
RUN bash anaconda.sh -b -p /opt/anaconda && \
    rm /opt/anaconda.sh && \
    chmod -R go-w /opt/anaconda && \
    chmod -R go+rX /opt/anaconda && \

# Market Reporter
USER root
RUN groupadd plu && \
    useradd --system --gid plu plu && \
    mkdir -p /opt/market-reporter && \
    chown -R plu:plu /opt/market-reporter
