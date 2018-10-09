# Market Reporter
[English](../README.md)

<p align="center"><img src="../docs/pics/logo.png"></p>

__Market Reporter__ は株価等の時系列データから、それを要約した短いテキストを自動で生成します。これは論文 Murakami et al. (ACL 2017) [[bib](#reference)] [[PDF](http://www.aclweb.org/anthology/P17-1126)] と Aoki et al. (INLG 2018) [[bib](#reference)] [PDF] のPythonによる実装です。

<p align="center"><img src="../docs/pics/gloss.png"></p>


## 目次
1. [準備](#準備)
    1. [構成](#構成)
    2. [資源](#資源)
    3. [EC2](#ec2)
    4. [S3](#s3)
    5. [Anaconda](#anaconda)
    6. [PostgreSQL](#postgresql)
2. [使い方](#使い方)
    1. [学習](#学習)
    2. [予測](#予測)
3. [Webインターフェース](#Webインターフェース)
4. [テスト](#テスト)
5. [参考文献](#参考文献)

## 準備
### 構成
システムの構成は以下の図のようになっています。
<p align="center"><img src="../docs/pics/architecture.png"></p>

[アイコンのクレジット](../docs/icon-credit-ja.md)

### 資源
+ 時系列データ
    時系列データは[Thomson Reuters DatScope Select](https://financial.thomsonreuters.com/en/products/infrastructure/financial-data-feeds/datascope-data-analytics-platform/datascope-select-data-delivery.html)との契約により利用可能になる[REST API](https://developers.thomsonreuters.com/datascope-select-dss/datascope-select-rest-api) を用いて取得しました。
+ テキストデータ
    日経QUICKニュース社から購入したものを使用しています。

### EC2
Amazon EC2を利用する場合、このレポジトリに含まれるAnsibleのスクリプトを使って環境構築をできるようになっています。
これによりPostgreSQL等の必要なソフトウェアもインストールすることができます。
```bash
pip install ansible
cd envs
cp hosts.example hosts
vi hosts # Edit variables according to your environment
ansible-playbook playbook.yaml
```

### Amazon S3
本ソフトウェアは[Amazon S3](https://aws.amazon.com/s3/)を使用します。
使用前に`AmazonS3FullAccess`が付与されていることを確認してください。
credential file.
詳細については公式のドキュメント[AWS Identity and Access Management](http://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html)をご覧ください。

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
必須ではありませんが<a href="https://www.anaconda.com/download/" target="_blank">Anaconda</a>を利用することをお薦めします。
AnacondaはPython 3用のものを使用してください。
Python 2用のものでは動きません。
インストール後`environment.yaml`を読み込んで新規の環境を作成します。

```bash
conda env create -f environment.yaml -n NAME
source activate NAME
```

### PostgreSQL
Ansibleを用いてインスタンスを作成した場合は既にインストールされています。
手動でインストールした場合は`python3-psycopg2`等のPython用のライブラリがインストールされていることを確認してください。
```bash
sudo apt install python3-psycopg2
```
データベースが使用しているマシン上にある場合、記述を簡略化することができます。
例えば `master` という名前のデータベースを利用する場合は以下のようになります。
```
[postgres]
- uri = 'postgresql://USERNAME:PASSWORD@SERVER:PORT/DATABASE'
+ uri = 'postgresql:///master'
```
SSHポートフォワーディングを用いてデータベースに接続する際は、まず
`~/.ssh/config` にデータベースがあるサーバーの情報を記述します。

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
例えばポート`2345` を使用する場合は以下のようなコマンドを実行して接続します。
```
ssh -L 2345:localhost:5432 dbserver # `5432` is the default port of PostgreSQL 
ssh -fNT -L 2345:localhost:5432 dbserver # `-fNT` options keep connection in the background
```
この接続を行っている間、以下のようにしてデータベースに接続することができます。
```
psql -h localhost -p 2345 -U kirito master
```
このとき `config.toml` は以下のようになります。
```
- uri = 'postgresql://USERNAME:PASSWORD@SERVER:PORT/DATABASE'
+ uri = 'postgresql://kirito:PASSWORD@localhost:2345/master'
```


## 使い方

### 学習

まず、以下のコマンドのように、 [example.toml](https://github.com/aistairc/market-reporter/blob/master/example.toml) もしくは [murakami-et-al-2017.example.toml](https://github.com/aistairc/market-reporter/blob/master/murakami-et-al-2017.example.toml) をコピーし、 `config.toml` を作成してください。その後、実行環境に応じてファイルを編集してください。

```bash
cp example.toml config.toml
vi config.toml
```

モデルを学習するためは以下のコマンドを実行してください。 GPU (CPU) を使用する場合は、 `--device` に `cuda:n` (`cpu`) を与えてください。 `n` は使用したい GPU デバイスの番号です。
```bash
python -m reporter --device 'cuda:0'
```

実行後、3 つのファイル (`reporter.log` と `reporter.model`、 `reporter.vocab`) が `config.output_dir/reporter-DATETIME` 以下に出力されます。 ここで、 `config.output_dir` は `config.toml` で設定した変数、 `DATETIME` はプログラム実行日時のタイムスタンプを表しています。

### 予測

学習後、出力ファイルを用いて、銘柄と時刻を指定することで概況テキストを生成することができます。

```bash
python -m reporter.predict \
    -r '.N225' \
    -t '2018-10-03 09:03:00+0900' \
    -o output/reporter-DATETIME
# -r, --ric: 銘柄（Reuters Instrument Codeを指定。例えば日経平均であれば'.N225'になります。）
# -t, --time: 時刻（'%Y-%m-%d %H:%M:%S%z'の形式で指定してください。）
# -o, --output: 学習で作られた、'reporter.model'と'reporter.vocab'を含むディレクトリを指定してください。
```


## Webインターフェース

以下のコマンドを実行し、ブラウザで `http://localhost:5000/` にアクセスしてください。

```bash
python -m reporter.webapp
```

サーバー環境で起動する際は、代わりに以下のコマンドを実行してください。

```bash
nohup uwsgi --ini uwsgi.ini &
```

正常に起動すると以下のような検索画面が表示されます。

<p align="center"><img src="../docs/pics/webapp.png"></p>

## テスト

```bash
python setup.py test
```

## 参考文献
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
  author = {Tatsuya Aoki
  }
  url = {http://www.aclweb.org/anthology/P17-1126}
}
```
