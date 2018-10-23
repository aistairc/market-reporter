FROM continuumio/anaconda3

RUN apt-get update && apt-get install -y \
    emacs \
    gcc \
    g++ \
    postgresql \    
    sudo \
    vim

RUN useradd -G sudo -m -s /bin/bash plu \
    && echo "plu:plumaketreporter" | chpasswd \
    && echo 'Defaults visiblepw' >> /etc/sudoers \
    && echo "plu ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER postgres

RUN /etc/init.d/postgresql start \
    && createuser plu \
    && createdb master plu

USER plu

ENV HOME /home/plu

RUN echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc \
    && echo "conda activate base" >> ~/.bashrc

RUN mkdir -p ${HOME}/market-reporter

WORKDIR ${HOME}/market-reporter

# TODO : when the repository is published, use 'wget ....zip' .
COPY --chown=plu:plu [".", "${HOME}/market-reporter/"]

CMD ["/bin/bash"]