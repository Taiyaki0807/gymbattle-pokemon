# Gym Battle Pokémon

ポケモンマスターズ EX のチーム向けに、約20人のメンバーと18タイプへの参加可否を管理する非公式Webアプリです。人数に固定の上限はありません。

## 機能

- 日本語のメンバー × 18タイプ対応表（横スクロール・固定の名前列）
- タイプごとに「可・条件付き・不可」と条件メモを保存
- メンバー追加・編集・削除（削除確認画面あり）
- 名前検索、タイプと参加可否による絞り込み。参加可否のみ指定すると、その状態のタイプを1つ以上持つメンバーを表示
- SQLiteへの永続化、ログイン必須、CSRF保護
- Django管理画面とGitHub Actionsによる自動テスト

## ローカル起動

Python 3.12〜3.14を推奨。Django 5.2 LTSを使用します。

```powershell
git clone https://github.com/Taiyaki0807/gymbattle-pokemon.git
cd gymbattle-pokemon
# PR未マージの場合
git switch codex/django-type-roster
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py createsuperuser
.venv\Scripts\python manage.py runserver
```

macOS/Linuxでは `.venv\Scripts\python` を `.venv/bin/python` に読み替えてください。

ブラウザーで http://127.0.0.1:8000/ を開き、作成したアカウントでログインします。「メンバーを追加」から名前と参加可否を入力してください。初期値はすべて「不可」です。実メンバーのデータは同梱していません。

管理画面は http://127.0.0.1:8000/admin/ です。複数の利用者が使う場合は、管理画面のユーザーから個別アカウントを作れます。ログイン可能な全ユーザーが全メンバーを閲覧・編集・削除できる、信頼できるチーム内向けの構成です。

## データとバックアップ

データはプロジェクト直下の `db.sqlite3` に保存され、再起動後も残ります。DB・仮想環境・秘密情報はGit管理対象外です。バックアップはアプリ停止中に `db.sqlite3` を別の場所にコピーしてください。新しいPCへ移す場合は、同じコードと依存関係を準備し、DBを配置して `migrate` を実行します。

## 検証

```powershell
.venv\Scripts\python manage.py check
.venv\Scripts\python manage.py makemigrations --check --dry-run
.venv\Scripts\python manage.py test
```

追加・更新・削除の永続化、18タイプ、複合フィルター、入力エラー、DB制約、認証・CSRF・HTMLエスケープをテストします。CIではPython 3.12と3.14で実行します。

## 構成と今後の拡張

- `config/`: 設定・URL・WSGI
- `roster/models.py`: MemberとParticipation。メンバーとタイプの組み合わせは一意
- `roster/constants.py`: 18タイプの定義
- `roster/forms.py`: 18タイプの入力とトランザクション単位の保存
- `roster/views.py`: 一覧・検索・編集・削除
- `roster/templates/roster/`、`roster/static/roster/`: 日本語UIとレスポンシブCSS
- `roster/migrations/`: DBの変更履歴。将来の機能追加時はマイグレーションを追加

参加可否を独立したモデルにしており、今後バディーズ情報やイベント単位の割り当てなどを追加できます。管理画面で作成されていないタイプのレコードは一覧で「未登録」と表示します。通常のメンバー編集画面で保存すると18タイプすべてが揃います。

## 公開運用する場合

ローカル起動は開発用です。共有サーバーへの配備はこのPRには含みません。

- `DJANGO_DEBUG=0`、ランダムな `DJANGO_SECRET_KEY`、`DJANGO_ALLOWED_HOSTS`（カンマ区切り）を環境変数に設定
- HTTPSとWSGIサーバーを利用し、`python manage.py collectstatic` で集約した静的ファイルを配信
- `python manage.py check --deploy` で配備設定を確認し、DBの定期バックアップを用意
- SQLiteファイルを永続ディスクに保存。利用規模拡大時はPostgreSQLへの移行を検討

`.env` ファイルの自動読み込みは行いません。環境変数は実行環境側で設定してください。公式画像・ロゴは使用していません。
