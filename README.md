# Gym Battle Pokémon

ポケモンマスターズ EX 向けの非公式チーム管理アプリ。Django 5.2 LTS / SQLiteを使用します。

## 表での操作

- 表の「＋」でメンバーが1行追加されます。専用の追加・編集画面はありません。
- 名前を直接入力し、各セルで「◎・〇・△・×・-」を選択します。初期値は×です。
- 18タイプをそれぞれ物理・特殊に分けた36セル構成。ノーマルは最後に並びます。
- 名前・記号・メモは変更後に自動保存されます。名前とメモは入力欄から移動すると保存します。
- 保存に失敗すると入力を保持し、赤枠の説明と「再保存」ボタンを表示します。
- 表示するタイプはチェックボックスで複数選択できます。「絞り込む」で選択したタイプの列だけを表示し、未選択なら18タイプすべてを表示します。ノーマルは常に最後です。
- 名前・物理/特殊・記号も組み合わせて絞り込みできます。タイプを複数選んだ場合は、選んだタイプのいずれかのセルが条件に一致するメンバーを表示します。
- 記号「-」は×と別の値として保存・検索できます。非表示のタイプのデータは保持され、＋で追加した後も選択したタイプを維持します。
- 表は横スクロールでき、名前列とヘッダーが固定されます。削除は確認画面付きです。
- ログインした全ユーザーが全メンバーを編集できる、信頼できるチーム内向けの構成です。
- JavaScriptが無効な場合は各入力の保存ボタンで保存できます。

## ローカル起動（PowerShell）

Python 3.12〜3.14を推奨します。

```powershell
git clone --branch codex/inline-type-matrix https://github.com/Taiyaki0807/gymbattle-pokemon.git
cd gymbattle-pokemon
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py createsuperuser
.\.venv\Scripts\python manage.py runserver
```

http://127.0.0.1:8000/ を開き、作成したアカウントでログインします。
macOS/Linuxでは `.venv/Scripts/python` を `.venv/bin/python` に読み替えてください。
管理画面は `/admin/` です。ここから個別の利用者アカウントも追加できます。

## 既存版からの更新

サーバーを停止し、`db.sqlite3` を別の場所へコピーしてから更新してください。

```powershell
git pull --ff-only origin codex/inline-type-matrix
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py runserver
```

既存の可・条件付き・不可はそれぞれ〇・△・×として、物理・特殊の両方に記号と条件メモを引き継ぎます。
物理と特殊を区別する情報が旧データにはないため、移行後に表で調整してください。
メンバー名、メモ、アカウントは保持します。新しいDBマイグレーションはデータ損失を避けるため、旧形式へ戻す処理を提供しません。

## データと構成

DBは `db.sqlite3` に永続化します。DB・秘密情報・仮想環境はGit対象外です。
バックアップはアプリ停止中にSQLiteファイルをコピーしてください。

- `config/`: 設定・URL・WSGI
- `roster/models.py`: メンバーとタイプ別・分類別の記号。組み合わせごとに一意制約
- `roster/forms.py`: 入力値の検証
- `roster/views.py`: 一覧・絞り込み・行追加・セル更新・削除
- `roster/templates/roster/`、`roster/static/roster/`: 日本語UIと表の自動保存
- `roster/migrations/`: スキーマと既存データの移行

## テスト

```powershell
.\.venv\Scripts\python manage.py check
.\.venv\Scripts\python manage.py makemigrations --check --dry-run
.\.venv\Scripts\python manage.py test
```

行追加・36セル・記号の個別更新・名前変更・入力エラー・検索・認証・CSRF・DB制約・既存データ移行を検証します。
GitHub ActionsではPython 3.12と3.14で実行します。

## 公開運用

開発サーバーによるローカル利用を想定しています。配備時は以下を設定してください。

- 環境変数 `DJANGO_DEBUG=0`、ランダムな `DJANGO_SECRET_KEY`、`DJANGO_ALLOWED_HOSTS`（カンマ区切り）
- HTTPS、WSGIサーバー、`collectstatic` による静的ファイル配信
- `manage.py check --deploy` による設定確認、永続ディスクと定期バックアップ

`.env` の自動読み込みはありません。公式画像・ロゴは使用していません。
