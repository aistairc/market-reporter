# Market Reporter
[日本語](docs/README-ja.md)

<p align="center"><img src="docs/pics/logo.png"></p>

__Market Reporter__ is a tool that automatically generates market comments from time series data of prices.

## Table of Contents
1. [About](#about)
2. [Requirements](#requirements)
    1. [Architecture](#architecture)
    2. [Resources](#resources)
    3. [EC2](#ec2)
    4. [S3](#s3)
    5. [Anaconda](#anaconda)
    6. [PostgreSQL](#postgresql)
    7. [Redis](#redis)   
3. [Usage](#usage)
4. [Web Interface](#web-interface)
5. [Test](#test)
6. [License and Reference](#license-and-reference)

## About
This is an implementation of [Murakami et al. 2017](#reference) and [Aoki et al. 2018](#reference).
Given sequences of prices, it generates a short summary describing them.
Examples are shown in the following picture, which was taken from the web interface for human evaluation in debug mode.
<p align="center"><img src="docs/pics/webapp-human-evaluation-debug.png"></p>


## Requirements
### Architecture
The architecture is illustrated below.
<p align="center"><img src="docs/pics/architecture.png"></p>

[Credit of the icons](docs/icon-credit.md)

### Resources
+ Tick data  
    We purchased tick data from [Thomson Reuters DatScope Select](https://financial.thomsonreuters.com/en/products/infrastructure/financial-data-feeds/datascope-data-analytics-platform/datascope-select-data-delivery.html) and downloaded them by using the [REST API](https://developers.thomsonreuters.com/datascope-select-dss/datascope-select-rest-api) it provides.
+ Text data  
    We purchased news articles provided by Nikkei Quick News.

### EC2
When you use Amazon EC2, launch an instance by Ansible.
The script installs PostgreSQL, Redis, and the other dependencies on it.
```bash
pip install ansible
cd envs
cp hosts.example hosts
vi hosts # Edit variables according to your environment
ansible-playbook playbook.yaml
```

### Amazon S3
This tool stores data to [Amazon S3](https://aws.amazon.com/s3/).
Ask the manager to give you `AmazonS3FullAccess` and issue a credential file.
For details, please read [AWS Identity and Access Management](http://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html).

```bash
mkdir -p "$HOME/.aws"
chmod 700 "$HOME/.aws"
touch "$HOME/.aws/credentials"
chmod 600 "$HOME/.aws/credentials"
# Change `PROFILE_NAME` to `default` or something.
echo '[PROFILE_NAME]' >> credentials
# Change `$HOME/Downloads/creadenticals.csv` according to your environment.
downloaded_credentials="$HOME/Downloads/credentials.csv"
cat $downloaded_credentials \
    | awk 'BEGIN { FS = ","; } NR == 2 { print $3; }' \
    | sed -e 's/^/aws_access_key_id=/' \
    >> credentials
cat $downloaded_credentials \
    | awk 'BEGIN { FS = ","; } NR == 2 { print $4; }' \
    | sed -e 's/^/aws_secret_access_key=/' \
    >> credentials
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
PostgreSQL is installed by Ansible.
When you install it manually, be sure you have `python3-psycopg2`.
```bash
sudo apt install python3-psycopg2
```
When you use your database named `master` on your local machine, edit `config.toml` as follows.
```
[postgres]
- uri = 'postgresql://USERNAME:PASSWORD@SERVER:PORT/DATABASE'
+ uri = 'postgresql:///master'
```
When you connect to a database server using SSH port forwarding,
first add the configuration for the server to `~/.ssh/config`
if you have not added it.

```
# ~/.ssh/config
Host dbserver
    HostName ec2-xxx-xxx-xxx-xxx.ap-northeast-1.compute.amazonaws.com
    User kirito
    IdentityFile ~/.ssh/kirito.pem
    IdentitiesOnly yes
    ForwardAgent yes
    ServerAliveInterval 60
```
Then connect to the server on some port, say `2345`.
```
ssh -L 2345:localhost:5432 dbserver # `5432` is the default port of PostgreSQL 
ssh -fNT -L 2345:localhost:5432 dbserver # `-fNT` options keep connection in the background
```
While keeping the connection above, you can access to the database on your local machine.
```
psql -h localhost -p 2345 -U kirito master
```
Then edit `config.toml`.
```
- uri = 'postgresql://USERNAME:PASSWORD@SERVER:PORT/DATABASE'
+ uri = 'postgresql://kirito:PNdWzhR2rzqUXW4n4GGRa7bN@localhost:2345/master'
```

### Redis

The settings are written as below in the config file.

```
[redis]
host = 'localhost'
port = 6379
db = -1
```
The variable `db` is set to `-1` by default to prevent exisiting data from being overwritten.
Please change it to a nonnegative integer.


## Usage

```bash
cp example.toml config.toml  # Create a configuration file
vi config.toml  # Edit some variables according to your environment
python -m reporter --device 'cuda:0'  # 'cpu' or 'cuda:n', where n is device index to select
```


## Web Interface

Execute the following command and access `http://localhost:5000/` in a web browser.

```bash
python -m reporter.webapp
```

When you launch it on a server, execute the following command instead.
```bash
nohup uwsgi --ini uwsgi.ini &
```

You can see a page as the following picture.
<p align="center"><img src="docs/pics/webapp.png"></p>

## Test

```bash
python setup.py test
```

## License and Reference
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
  }
  title = {Generating Market Comments Referring to External Resources}
  booktitle = {Proceedings of the 11th International Conference on
               Natural Language Generation},
  year = {2018},
  publisher = {Association for Computational Linguistics},
  pages = {},
  location = {},
  doi = {},
  url = {}
}
```
