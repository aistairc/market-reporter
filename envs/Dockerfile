FROM postgres:10.5

ENV DEBCONF_NOWARNINGS yes
ENV PATH /opt/anaconda/bin:$PATH

RUN apt-get update && apt-get -y install \
    git \
    nginx \
    vim-tiny \
    wget

# Anaconda
RUN mkdir -p /opt && \
    wget --quiet https://repo.anaconda.com/archive/Anaconda3-5.3.0-Linux-x86_64.sh -O anaconda.sh && \
    bash anaconda.sh -b -p /opt/anaconda && \
    rm anaconda.sh && \
    groupadd anaconda && \
    useradd --system --gid anaconda anaconda && \
    chmod -R go-w /opt/anaconda && \
    chmod -R go+rX /opt/anaconda && \
    groupadd plu && \
    useradd --system --gid plu plu && \
    mkdir -p /opt/market-reporter && \
    chown -R plu:plu /opt/market-reporter

COPY nginx.conf /etc/nginx/conf.d/market-reporter.conf
