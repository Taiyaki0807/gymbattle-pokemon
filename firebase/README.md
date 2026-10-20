# Firebase版 Gym Battle

画像を使わず、同じ共有URLから全員が同じ表を閲覧・編集する版です。
Firebase Hosting（画面の公開）＋Cloud Firestore（表の保存）＋匿名認証（内部で自動接続）を使います。
Django、Cloud Functions、App Hosting、Cloud Storage、課金アカウントは不要です。
既存Django版はリポジトリに残してあります。

## Firebaseを初めて使う場合

Firebaseは「Googleが提供する、画面と共有データの置き場所」です。
プロジェクトはこのアプリ専用の入れ物で、以下の設定は管理者だけが行います。
利用者は完成した共有URLを開くだけです。Googleログインや利用者登録は不要です。

### 1. 無料のプロジェクトを作る

1. https://console.firebase.google.com/ をGoogleアカウントで開きます。
2. プロジェクトを作成します。Google Analyticsはこのアプリでは不要なので無効で構いません。
3. プロジェクトの料金プランは **Spark（無料）** のままにします。カード登録やBlazeへの変更は不要です。
4. 歯車 → プロジェクトの設定 → マイアプリでWebアプリ（`</>`）を追加します。
5. 表示された `firebaseConfig` の `apiKey`、`authDomain`、`projectId`、`appId` を控えます。

これらはブラウザーで使う接続情報です。サービスアカウントの秘密鍵は使いません。

### 2. 認証とデータベースを有効にする

1. Build → Authentication → 始める → ログイン方法 → **匿名** を有効にします。
2. Build → Firestore Database → データベースを作成します。Standard editionのデフォルトDBを使います。
3. セキュリティルールは本番モードで始めてください。テストモードの「全員許可」にはしません。
4. 管理コンソールからコレクション `boards` を作成します。
5. 次のコマンドで共有IDを生成し、その値をドキュメントIDに指定します。

```powershell
npm run board-id
```

6. そのドキュメントに `enabled` をboolean型の `true`、`schemaVersion` をnumber型の `1` として保存します。

共有IDは48文字のランダム値です。短い名前やプロジェクトIDを使わないでください。
Firebaseの管理画面から作るため、サイト訪問者が新たな共有表を勝手に作ることはできません。

### 3. 接続設定と公開

Node.js 22.12以上（または24）を用意し、このフォルダで実行します。

```powershell
npm ci
Copy-Item .env.example .env.local
```

`.env.local` に手順1の接続情報を入力します。

```text
VITE_FIREBASE_API_KEY=取得したapiKey
VITE_FIREBASE_AUTH_DOMAIN=取得したauthDomain
VITE_FIREBASE_PROJECT_ID=取得したprojectId
VITE_FIREBASE_APP_ID=取得したappId
VITE_USE_EMULATORS=false
```

続けて次を実行します。途中でGoogleのログイン画面が開いたら、プロジェクト所有者のアカウントでログインします。

```powershell
npx firebase login
npx firebase use --add
npm run deploy
```

HostingのURLが表示されます。URLの末尾に `#b=共有ID` を付けたものをメンバーへ渡します。

```text
https://プロジェクト名.web.app/#b=48文字の共有ID
```

Firebaseの「App Hosting」とは別の、通常の「Hosting」を使います。
ルールも同時に配備し、メンバーの読み書きを対象の共有ID内に制限します。

## 操作と保存

- ＋でメンバーを1行追加し、名前・記号・メモを表内で編集
- 記号は◎・〇・△・×・-、タイプごとに物理／特殊。ノーマルは最後
- 表示タイプを複数選択。名前・記号・物理特殊でも絞り込み
- 保存のたびにFirestoreへ書き込み、他の利用者にも反映。同じセルの同時編集は最後にサーバーへ保存された値になります
- 違うセルは別フィールドとして更新し、他の人の変更を上書きしません
- 保存できないときは入力を残し、再保存ボタンを表示。保存中はページを閉じないでください
- 「表をバックアップ」でJSONをダウンロード可能。読み込みは既存の表を消さず追加します
- 画像の表示・アップロード機能はありません

**共有URLはパスワードと同様に扱ってください。転送された相手も閲覧・編集できます。**
匿名認証は本人確認ではありません。この版は、退会者を個別に締め出さないという方針です。
一覧検索で他の共有IDを取得することはできませんが、URLの秘密性だけに頼りたくない場合は個別ログイン版へ変更してください。
共有を止めるにはFirebaseコンソールで該当するboardの `enabled` を `false` にします。
無料枠の使用量はFirebaseコンソールで確認し、バックアップも定期的に保存してください。

## Django版の表を移す

Djangoアプリのフォルダで次を実行します。元のDBは変更しません。

```powershell
.\.venv\Scripts\python scripts\export_for_firebase.py --output firebase\team-data.json
```

Firebase版の共有URLを開き、「バックアップから追加」で `team-data.json` を選びます。
メンバー名・メモ・36セルの記号と条件のみ移します。Djangoのアカウント・パスワード・セッション・画像は移しません。
書き出したJSONはGitに追加しないでください。既に同名ファイルがある場合、書き出しは上書きせず止まります。

## ローカルテスト

Java 21以上も必要です。エミュレーターはテスト用DBなので実データを使わないでください。

```powershell
npm test
npm run test:rules
npm run emulators
```

別のターミナルでこのフォルダを開きます。

```powershell
node scripts\seed-emulator.mjs
$env:VITE_USE_EMULATORS="true"
npm run dev
```

seedコマンドが表示したURLを開きます。このテスト用共有IDは本番では使わないでください。
ローカル確認後は `Remove-Item Env:VITE_USE_EMULATORS` で環境変数を外します。
公開ビルドでこの変数がtrueだと、公開先では接続を拒否します。

公式ドキュメント：
- https://firebase.google.com/docs/hosting/quickstart
- https://firebase.google.com/docs/firestore/security/rules-conditions
- https://firebase.google.com/docs/auth/web/anonymous-auth
- https://firebase.google.com/pricing
