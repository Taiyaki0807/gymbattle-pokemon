# PythonAnywhere無料プランでの公開

公式ガイド：
- https://help.pythonanywhere.com/pages/DeployExistingDjangoProject/
- https://help.pythonanywhere.com/pages/PythonVersions/
- https://help.pythonanywhere.com/pages/FreeAccountsFeatures/

Python 3.13での手順です。WebアプリのPythonと仮想環境のバージョンを揃えてください。
新規無料アカウントではSQLiteを使用します。無料枠は容量512MiB・1ワーカーなので、画像を圧縮し、実際の同時編集で動作を確認してください。

## 1. コードと依存関係

PythonAnywhereのConsolesでBashを開きます。

```bash
git clone --branch codex/inline-type-matrix https://github.com/Taiyaki0807/gymbattle-pokemon.git
cd ~/gymbattle-pokemon
python3.13 -m venv .venv
source .venv/bin/activate
pip install --no-cache-dir -r requirements.txt
```

既に取得済みなら新しくクローンせず、該当フォルダで `git pull --ff-only` を実行します。

## 2. 公開用設定を生成

以下の `YOUR_USERNAME` は自分のユーザー名に置き換えてください。
EU環境の場合は `YOUR_USERNAME.eu.pythonanywhere.com` を指定します。

```bash
python scripts/configure_pythonanywhere.py --hostname YOUR_USERNAME.pythonanywhere.com
```

秘密鍵は `.pythonanywhere.json` にランダム生成されます。Git対象外で、画面にも表示しません。
再実行しても同じ設定と秘密鍵を維持し、DBや画像は上書きしません。
DBと画像はコードと分けて `data/db.sqlite3`、`data/media/` に保存します。
公開用設定は `config.pythonanywhere`、ローカル用設定は従来の `config.settings` です。

## 3. データを引き継ぐ場合

新規で始める場合はこの段階を飛ばします。

ローカル側で、SQLiteの整合性を保ったコピーと `media/` 内の画像を同じフォルダに用意します。
PythonAnywhereのFiles画面を使い、DBを `~/gymbattle-pokemon/data/db.sqlite3` に、画像を `~/gymbattle-pokemon/data/media/` に配置します。
DBにはメンバー・アカウント・画像の参照が含まれるため、GitHubへはアップロードしないでください。
既に公開先にDBがある場合は、利用を止めてバックアップしてから移行します。既存DBへ上書きしないでください。
移行した場合、既存のユーザー名とパスワードを使えます。セッションは新しい秘密鍵で無効になるので再ログインが必要です。

## 4. DBと静的ファイルを準備

```bash
python manage.py migrate --settings=config.pythonanywhere
python manage.py collectstatic --noinput --settings=config.pythonanywhere
python manage.py check --deploy --settings=config.pythonanywhere
```

DBを引き継がず新規開始した場合は管理者も作成します。

```bash
python manage.py createsuperuser --settings=config.pythonanywhere
```

## 5. Webアプリを登録

Webタブ → Add a new web app → 無料のホスト名 → **Manual configuration** → **Python 3.13** を選びます。
既存プロジェクトなので、Djangoの新規プロジェクト作成メニューは使いません。

- Source code / Working directory：`/home/YOUR_USERNAME/gymbattle-pokemon`
- Virtualenv：`/home/YOUR_USERNAME/gymbattle-pokemon/.venv`
- WebタブのWSGI configuration fileを開き、内容を `deploy/pythonanywhere_wsgi.generated.py` の内容に置き換えます。このファイルは手順2で実際のパスに合わせて生成済みです。
- Static filesにはURL `/static/`、Directory `/home/YOUR_USERNAME/gymbattle-pokemon/staticfiles` を登録します。
- **`/media/` はStatic filesに登録しないでください。** 画像はアプリがログインを確認して配信します。直接配信すると退会者も画像URLを開けてしまいます。
- HTTPS関連の設定があればForce HTTPSを有効にします。アプリ側でもHTTPSへの転送を行います。
- Reloadボタンで反映します。

## 6. 公開後の確認

`https://YOUR_USERNAME.pythonanywhere.com/` を開き、以下を確認します。

- 未ログインでは表も画像も表示されない
- あなたの管理者アカウントで管理画面が使える
- 通常アカウントで表を編集でき、管理画面には入れない
- タイプの複数選択、記号の保存、画像のアップロードと表示が動く
- アカウントを無効にするとログイン済みの端末も次の操作から拒否される

更新時はBashで `git pull --ff-only`、依存関係のインストール、手順4を実行してWebタブのReloadを押します。
変更前には `data/` と `.pythonanywhere.json` のバックアップを取ってください。
無料アプリは期限があるため、Webタブで公開期限を定期的に延長してください。
