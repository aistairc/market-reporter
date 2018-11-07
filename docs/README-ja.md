# Market Reporter
[English](../README.md)

<p align="center"><img src="../docs/figures/logo.svg" width="600px"></p>

__Market Reporter__ は株価等の時系列データから、それを要約した短いテキストを自動で生成します。これは論文 Murakami et al. (ACL 2017) [[bib](#reference)] [[paper](http://www.aclweb.org/anthology/P17-1126)] と Aoki et al. (INLG 2018) [[bib](#reference)] [[paper](http://aclweb.org/anthology/W18-6515)] [[poster](figures/pdf/poster.pdf)] のPythonによる実装です。

<p align="center"><img src="../docs/figures/gloss.svg" width="100%"></p>


## 目次
1. [準備](#準備)
    1. [構成](#構成)
    2. [資源](#資源)
    3. [S3](#s3)
    4. [Docker](#docker)
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
<p align="center"><img src="../docs/figures/architecture.svg" width="100%"></p>

[アイコンのクレジット](../docs/icon-credit-ja.md)

### 資源
+ 時系列データ
    時系列データは[Thomson Reuters DatScope Select](https://financial.thomsonreuters.com/en/products/infrastructure/financial-data-feeds/datascope-data-analytics-platform/datascope-select-data-delivery.html)との契約により利用可能になる[REST API](https://developers.thomsonreuters.com/datascope-select-dss/datascope-select-rest-api) を用いて取得しました。
+ テキストデータ
    日経QUICKニュース社から購入したものを使用しています。

### Amazon S3
本ソフトウェアは[Amazon S3](https://aws.amazon.com/s3/)を使用します。
使用前に`AmazonS3FullAccess`が付与されていることを確認してください。
詳細については公式のドキュメント[AWS Identity and Access Management](http://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html)をご覧ください。

### Docker
AWS の認証プロファイル（通常は `~/.aws/credetials`）を使用する場合は `config.toml` の `s3` セクションにある `profile_name` を設定してください。
認証プロファイルを使用しない場合、Docker イメージ起動時に AWS access key ID と AWS secret access key を入力する必要があります。

```bash
cd envs
docker build -t market-reporter .
docker run -d \
    --name demo \
    --user root \
    --volume /opt/ \
    --publish 443:443 \
    -e AWS_ACCESS_KEY_ID=your_access_key_id \
    -e AWS_SECRET_ACCESS_KEY=your_secret_access_key \
    market-reporter
docker exec -it --user reporter demo /bin/bash
```

### Anaconda
必須ではありませんが<a href="https://www.anaconda.com/download/" target="_blank">Anaconda</a>を利用することをお薦めします。AnacondaはPython 3用のものを使用してください。Python 2用のものでは動きません。インストール後`environment.yaml`を読み込んで新規の環境を作成します。

```bash
conda env create -f environment.yaml -n NAME
source activate NAME
```

### PostgreSQL
例えば自分のマシン上にある `master` という名前のデータベースを利用する場合、`config.toml` を以下のように編集します。
```
[postgres]
- uri = 'postgresql://USERNAME:PASSWORD@SERVER:PORT/DATABASE'
+ uri = 'postgresql:///master'
```
SSHポートフォワーディングを用いてリモートマシンのデータベースを利用している場合（例：`ssh -fNT -L 2345:localhost:5432 kirito@dbserver`）、以下のように編集します。
```
- uri = 'postgresql://USERNAME:PASSWORD@SERVER:PORT/DATABASE'
+ uri = 'postgresql://kirito:PASSWORD@localhost:2345/master'
```

## 使い方

### 学習

設定ファイルの例 [example.toml](https://github.com/aistairc/market-reporter/blob/master/example.toml) または [murakami-et-al-2017.example.toml](https://github.com/aistairc/market-reporter/blob/master/murakami-et-al-2017.example.toml) をコピー・編集し、 `config.toml` を作成してください。

モデルを学習するためは以下のコマンドを実行してください。GPU (CPU) を使用する場合は、`--device` オプションで `cuda:n` (`cpu`) を指定してください。ここで `n` は使用する GPU デバイスの番号です。
```bash
python -m reporter --device 'cuda:0'
```

実行後、3 つのファイル (`reporter.log` と `reporter.model`、 `reporter.vocab`) が `config.output_dir/reporter-DATETIME` 以下に出力されます。 ここで、 `config.output_dir` は `config.toml` で設定した変数、 `DATETIME` はプログラム実行日時のタイムスタンプを表しています。

### 予測

学習後、出力ファイルを用いて、銘柄と時刻を指定することで概況テキストを生成することができます。

```bash
# -r, --ric: 銘柄（Reuters Instrument Codeを指定してください。例えば日経平均の場合'.N225'になります。）
# -t, --time: 時刻（'%Y-%m-%d %H:%M:%S%z'の形式で指定してください。）
# -o, --output: 学習で作られた'reporter.model'と'reporter.vocab'を含むディレクトリを指定してください。
python -m reporter.predict \
    -r '.N225' \
    -t '2018-10-03 09:03:00+0900' \
    -o output/reporter-2018-10-07-18-47-41
```


## Webインターフェース

以下のコマンドを実行し、ブラウザで `http://localhost:5000/` にアクセスしてください。

```bash
make  # for the first time
python -m reporter.webapp
```

サーバー環境で起動する際は、代わりに以下のコマンドを実行してください。

```bash
nohup uwsgi --ini uwsgi.ini &
```

正常に起動すると以下のような検索画面が表示されます。

<p align="center"><img src="../docs/figures/webapp.png"></p>

## テスト

```bash
python setup.py test
```

## ライセンスと参考文献
Market Reporterは以下のいずれかのライセンスで利用可能です。

+ [GNU General Public License (v3 or later)](https://www.gnu.org/licenses/gpl-3.0.en.html)
+ 商用ライセンス

商用ライセンスはソースコードを公開できないような場合に適しています。詳細については [kirt-contact-ml@aist.go.jp](kirt-contact-ml@aist.go.jp) までご連絡ください。


このソフトウェアには特許出願中の技術が含まれます（出願番号：2017001583）。

このソフトウェアを利用した論文を書く場合は、以下のいずれかまたは両方を引用してください。

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
  title = {Generating Market Comments Referring to External Resources},
  booktitle = {Proceedings of the 11th International Conference on Natural Language Generation},
  year = {2018},
  publisher = {Association for Computational Linguistics},
  pages = {135--139},
  location = {Tilburg University, The Netherlands},
  url = {http://aclweb.org/anthology/W18-6515}
}
```
