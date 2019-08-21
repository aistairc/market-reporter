# Market Reporter

[![CircleCI](https://circleci.com/gh/aistairc/market-reporter.svg?style=svg)](https://circleci.com/gh/aistairc/market-reporter)

[日本語](docs/README-ja.md)

<p align="center"><img src="docs/figures/logo.svg" width="600px"></p>

__Market Reporter__ automatically generates short comments that describe time series data of stock prices, FX rates, etc.
This is an implementation of Murakami et al. (ACL 2017) [[bib](#reference)] [[paper](http://www.aclweb.org/anthology/P17-1126)] and Aoki et al. (INLG 2018) [[bib](#reference)] [[paper](http://aclweb.org/anthology/W18-6515)] [[poster](figures/pdf/poster.pdf)].

<p align="center"><img src="docs/figures/gloss.svg" width="100%"></p>

## Table of Contents
1. [Requirements](#requirements)
    1. [Architecture](#architecture)
    2. [Resources](#resources)
    3. [S3](#s3)
    4. [Docker](#docker)
    5. [Anaconda](#anaconda)
    6. [PostgreSQL](#postgresql)
2. [Usage](#usage)
    1. [Training](#training)
    2. [Prediction](#prediction)
3. [Web Interface](#web-interface)
4. [Test](#test)
5. [License and References](#license-and-references)
6. [Copyright and Acknowledgment](#copyright-and-acknowledgment)


## Requirements
### Architecture
The architecture is illustrated below.
<p align="center"><img src="docs/figures/architecture.svg" width="100%"></p>

[Credit of the icons](docs/icon-credit.md)

### Resources
+ Tick data  
    We purchased tick data from [Thomson Reuters DatScope Select](https://financial.thomsonreuters.com/en/products/infrastructure/financial-data-feeds/datascope-data-analytics-platform/datascope-select-data-delivery.html) and downloaded them by using the [REST API](https://developers.thomsonreuters.com/datascope-select-dss/datascope-select-rest-api) it provides.
+ Text data  
    We purchased news articles provided by Nikkei Quick News.

### Amazon S3
This tool stores data to [Amazon S3](https://aws.amazon.com/s3/).
Ask the manager to give you `AmazonS3FullAccess` and issue a credential file.
For details, please read [AWS Identity and Access Management](http://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html).


### Docker
Install Docker and Docker Compose.
Edit [envs/docker-compose.yaml](envs/docker-compose.yaml) according to your environment.
Then, launch containers by `docker-compose`.
```bash
# Install Docker
sudo apt-get update
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository \
    "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) \
    stable"
sudo apt-get update
sudo apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/1.24.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

# Start Docker and log in
cd envs
sudo service docker start
sudo docker-compose up -d
sudo exec --user reporter -it CONTAINER /bin/bash
```

### Anaconda
We recommend <a href="https://www.anaconda.com/download/" target="_blank">Anaconda</a>.
The code never runs on Python 2.
After you install Anaconda, create a new environment from `environment.yaml`.

```bash
conda env create -f environment.yaml -n NAME
source activate NAME
```

### PostgreSQL
Suppose you have a database named `master` on your local machine.
Then, edit `config.toml` as the following.
```
[postgres]
- uri = 'postgresql://USERNAME:PASSWORD@SERVER:PORT/DATABASE'
+ uri = 'postgresql:///master'
```

## Usage

### Training

Create `config.toml` based on [example.toml](https://github.com/aistairc/market-reporter/blob/master/example.toml) or [murakami-et-al-2017.example.toml](https://github.com/aistairc/market-reporter/blob/master/murakami-et-al-2017.example.toml).

Execute the following command for the training of model. When you use GPU (CPU), you specify `cuda:n`(`cpu`) for `--device` option, where `n` is the device index to use.
```bash
python -m reporter --device 'cuda:0'
```

After the program finishes, it saves three files (`reporter.log`, `reporter.model`, and `reporter.vocab`) to `config.output_dir/reporter-DATETIME`, where `config.output_dir` is a variable set in `config.toml` and `DATETIME` is the timestamp of the starting time.

### Prediction

Prediction submodule generates a single comment of a financial instrument at specified time by loading a trained model.

```bash
# -r, --ric: Reuters Instrument Code (e.g. '.N225' for Nikkei Stock Average)
# -t, --time: timestamp in '%Y-%m-%d %H:%M:%S%z' format
# -o, --output: directory that contains 'reporter.model' and 'reporter.vocab'
python -m reporter.predict \
    -r '.N225' \
    -t '2018-10-03 09:03:00+0900' \
    -o output/reporter-2018-10-07-18-47-41
```


## Web Interface

Execute the following command and access `http://localhost:5000/` in a web browser.

```bash
make  # for the first time
python -m reporter.webapp
```

When you launch it on a server, execute the following command instead.
```bash
nohup uwsgi --ini uwsgi.ini &
```

You can see a page as the following picture.
<p align="center"><img src="docs/figures/webapp.png"></p>
The web application can be used for evaluation.
Along with the generated sentences, it also shows the movements of prices used in generation.
<p align="center"><img src="docs/figures/webapp-graph.png"></p>

## Test

```bash
python setup.py test
```

## License and References
Market Reporter is available under different licensing options:

+ [GNU General Public License (v3 or later)](https://www.gnu.org/licenses/gpl-3.0.en.html).
+ Commercial licenses.

Commercial licenses are appropriate for development of proprietary/commercial software where you do not want to share any source code with third parties or otherwise cannot comply with the terms of the GNU.
For details, please contact us at [kirt-contact-ml@aist.go.jp](kirt-contact-ml@aist.go.jp)

This software uses a technique applied for patent (patent application number 2017001583).

When you write a paper using this software, please cite either or both of the followings.

```
@InProceedings{murakami2017,
  author = {Murakami, Soichiro
            and Watanabe, Akihiko
            and Miyazawa, Akira
            and Goshima, Keiichi
            and Yanase, Toshihiko
            and Takamura, Hiroya
            and Miyao, Yusuke},
  title = {Learning to Generate Market Comments from Stock Prices},
  booktitle = {Proceedings of the 55th Annual Meeting of
               the Association for Computational Linguistics (Volume 1: Long Papers)},
  year = {2017},
  publisher = {Association for Computational Linguistics},
  pages = {1374--1384},
  location = {Vancouver, Canada},
  doi = {10.18653/v1/P17-1126},
  url = {http://www.aclweb.org/anthology/P17-1126}
}

@InProceedings{aoki2018,
  author = {Aoki, Tatsuya
            and Miyazawa, Akira
            and Ishigaki, Tatsuya
            and Goshima, Keiichi
            and Aoki, Kasumi
            and Kobayashi, Ichiro
            and Takamura, Hiroya
            and Miyao, Yusuke},
  title = {Generating Market Comments Referring to External Resources},
  booktitle = {Proceedings of the 11th International Conference on Natural Language Generation},
  year = {2018},
  publisher = {Association for Computational Linguistics},
  pages = {135--139},
  location = {Tilburg University, The Netherlands},
  url = {http://aclweb.org/anthology/W18-6515}
}
```

## Copyright and Acknowledgment
© 2018 Akira Miyazawa, Tatsuya Aoki, Fumiya Yamamoto, Soichiro Murakami, and Akihiko Watanabe (National Institute of Advanced Industrial Science and Technology; AIST)

This software is based on results obtained from a project commissioned by the New Energy and Industrial Technology Development Organization (NEDO).
