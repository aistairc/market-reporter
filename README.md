# Market Reporter
[日本語](docs/README-ja.md)

<p align="center"><img src="docs/pics/logo.png"></p>

__Market Reporter__ automatically generates short comments that describe time series data of stock prices, FX rates, etc.
This is an implementation of Murakami et al. (ACL 2017) [[bib](#reference)] [[PDF](http://www.aclweb.org/anthology/P17-1126)] and Aoki et al. (INLG 2018) [[bib](#reference)] [PDF].

<p align="center"><img src="docs/pics/gloss.png"></p>

## Table of Contents
1. [Requirements](#requirements)
    1. [Architecture](#architecture)
    2. [Resources](#resources)
    3. [EC2](#ec2)
    4. [S3](#s3)
    5. [Anaconda](#anaconda)
    6. [PostgreSQL](#postgresql)
2. [Usage](#usage)
    1. [Training](#training)
    2. [Prediction](#prediction)
3. [Web Interface](#web-interface)
4. [Test](#test)
5. [References](#references)

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
The script installs dependencies such as PostgreSQL.
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

## Usage

### Training

Create a configuration file (default: `config.toml`). Please copy [example.toml](https://github.com/aistairc/market-reporter/blob/master/example.toml) or [murakami-et-al-2017.example.toml](https://github.com/aistairc/market-reporter/blob/master/murakami-et-al-2017.example.toml) and edit it according to your environment.

```bash
cp example.toml config.toml
vi config.toml
```

Execute the following command for the training of model. When you use GPU (CPU), you specify `cuda:n`(`cpu`) in `--device`, where n is device index to select.

```bash
python -m reporter --device 'cuda:0'
```

After the program finishes, it saves three files (`reporter.log`, `reporter.model`, and `reporter.vocab`) to `config.output_dir/reporter-DATETIME`, where `config.output_dir` is a variable set in `config.toml` and `DATETIME` is the timestamp of the starting time.

### Prediction

After training, using the output files, you can generate market comment at the specified any time as the following command.

```bash
python -m reporter.predict -o output/reporter-DATETIME -t '2018-10-03 09:03:00+0900' -r '.N225'
# -o or --output: directory containing 'reporter.model' and 'reporter.vocab'
# -t or --time: time (format 'year-month-day hour:minute:second+timezone')
# -r or --ric: Reuters Instrument Code
#    	    (e.g. '.N225': Nikkei Stock Average, '.DJI': Dow Jones Industrial Average, etc.)
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

## References

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
  author = {Tatsuya Aoki,
            and Takamura, Hiroya
            and Miyao, Yusuke},
  }
  title = {Generating Market Comments Referring to External Resources}
  url = {}
}
```
