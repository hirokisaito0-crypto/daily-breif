# Cloudflare Pages + Access（自分だけが見る）

## このページの読み方（新卒・非エンジニア向け）

このドキュメントは、**日次ブリーフのサイトを「インターネット上に置くが、特定の人だけが見られる」ようにする**ための手順です。  
はじめて触る名前（サービス名・設定名）が多いので、**先にざっくり意味だけ押さえてから**、下の手順に進むと迷いにくいです。

---

## 用語ミニ辞典（ここだけ読んでも OK）

| 用語 | ひとことで |
|------|------------|
| **GitHub Pages** | GitHub が用意する「静的サイトのホスティング」。**URL を知っていれば基本的に誰でも開ける**公開前提の仕組み（鍵はかけにくい）。 |
| **静的サイト** | サーバーで毎回計算するのではなく、**あらかじめ作った HTML などのファイルをそのまま配る**サイト。このプロジェクトの `dist/` がそれに相当。 |
| **Cloudflare Pages** | Cloudflare が提供する静的サイトのホスティング。**GitHub Actions から自動でファイルをアップロード（デプロイ）**できる。 |
| **デプロイ（deploy）** | 作ったファイルを「本番として載せる」こと。ここでは **`dist/` を Cloudflare 上に反映する**イメージ。 |
| **Cloudflare Zero Trust（ゼロトラスト）** | 「社内ネットにいる＝安全」と決めつけず、**アクセスのたびに本人確認する**考え方のサービス群の総称（ブランド名）。 |
| **Access（アクセス）** | Zero Trust の一部。**「この URL はログインした人だけ」**といったルールをかけられる機能。 |
| **ポリシー（Policy）** | 「誰を許可するか」のルール。例：**このメールアドレスだけ許可**。 |
| **Self-hosted（セルフホステッド）** | 「自分が用意したドメイン／URL」に Access の保護をかけるタイプの設定。ここでは **`*.pages.dev` のサイト**にかける。 |
| **One-time PIN（ワンタイム PIN）** | **メールに一度だけ使える短いコード**が届き、それを入力してログインする方式（パスワードを別途覚えなくてよい）。 |
| **API トークン** | **プログラムが Cloudflare を操作するときのパスワードのようなもの**。人間のログインパスワードとは別に発行する。**漏れたら止めて再発行**が基本。 |
| **Account ID（アカウント ID）** | Cloudflare があなたのアカウントに付けている **識別子（英数字の並び）**。API 呼び出しで「どのアカウントか」を指定するときに使う。 |
| **GitHub Secrets** | GitHub リポジトリに保存する **秘密情報（トークンなど）**。ワークフローからだけ読め、**ログにそのまま出ないようにするための置き場**。 |
| **GitHub Actions / ワークフロー** | リポジトリに置いた **自動実行のレシピ**。プッシュや時刻で「ビルド・デプロイ」などを動かす。 |
| **Wrangler（ラングラー）** | Cloudflare 公式の **コマンドラインツール**。`wrangler pages deploy` で Pages にファイルを載せられる。 |
| **サブドメイン** | `daily-brief-private.pages.dev` の **`daily-brief-private` の部分**。サイトの「名前の一段左」。 |
| **403** | HTTP のエラーで「**このページは見せない（禁止）**」に近い意味。権限やトークン不足で返ることがある。 |

---

## なにを達成するか

GitHub Pages は **URL を知っていれば誰でも開ける**公開サイトになりがちです。**Cloudflare Pages** に `dist/` を載せ、**Cloudflare Zero Trust の Access** で「許可したメールだけログイン可」にすると、要件に近い「本人限定」になります。

---

## 全体の流れ（やることの順番）

1. Cloudflare アカウントを作る  
2. **Pages** にプロジェクトを作る（名前を決める）  
3. **API トークン**と **アカウント ID** を取得する  
4. GitHub の **Secrets** に入れる → Actions が **`wrangler pages deploy`** で毎回アップロード  
5. **Zero Trust → Access** でアプリを追加し、**自分のメールだけ許可**  
6. （任意）**GitHub Pages を止める** → 公開 URL を無くす  

---

## 1. Cloudflare にログイン・Pages プロジェクト名を決める

1. [Cloudflare Dashboard](https://dash.cloudflare.com/) にサインアップ／ログイン  
2. 左または上部から **Workers & Pages** → **Create** → **Pages**  
   - **Workers**：元々は「サーバーに近い処理」を動かすサービス。**Pages**：静的サイト向け。名前が並んでいるだけで、まずは Pages 側を選べばよいです。  
3. **Create a project** → とりあえず **Direct Upload** でプロジェクトだけ作成してもよいし、**後から GitHub 連携は不要**（このリポジトリは既に Actions でビルドしているため）  
4. **プロジェクト名**を決める（例: `daily-brief-private`）  
   → 後で使うのでメモする。公開 URL の一例は `https://daily-brief-private.pages.dev` のような形になります（**`pages.dev` は Cloudflare が用意するドメイン**）。

---

## 2. Account ID をコピーする

1. ダッシュボード右サイドバー **Workers & Pages** の下あたり、または **概要** に **Account ID** が表示されます。  
2. 32 文字くらいの英数字。**そのままコピー**してメモ。  
   - あとで「どの Cloudflare アカウントにデプロイするか」を指定するときに使います。

---

## 3. API トークンを作る（GitHub Actions 用）

**「GitHub の自動処理が、あなたの代わりに Cloudflare にアップロードする」ための鍵**です。人間がブラウザでログインするパスワードとは別物です。

1. 右上プロフィール → **My Profile** → **API Tokens**  
   （または **Manage account** → **API Tokens**）  
2. **Create Token** → **Create Custom Token** を選ぶ  
3. 名前: 例 `github-actions-pages-deploy`（あとで何用か分かればよい）  
4. 権限（Permissions）は目安として次を付与：

   - **Account**  
     - **Cloudflare Pages** → **Edit**（編集できる＝デプロイに必要な操作ができる、という意味合い）  
   - （無ければ）**Workers Scripts** や **Account Settings** の説明に従い、**Pages デプロイに必要な範囲**を選ぶ  

   ※画面は変わることがあるので、「Pages にデプロイできる」旨が含まれていればよいです。

5. **Continue to summary** → **Create Token**  
6. **トークンはこの一度だけ表示**されるので、必ずコピーして安全な場所に保存。  
   - 漏れた・貼り間違えた可能性があれば **無効化して作り直し**が安全です。

---

## 4. GitHub に Secrets を登録する

**GitHub Actions がトークンを読めるようにする**設定です。ソースコードに直接書かず、**Secrets にだけ置く**のがポイントです。

リポジトリ → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

次の **3 つ**を追加します（名前は一字一句同じに）。

| Name | 値 |
|------|-----|
| `CLOUDFLARE_API_TOKEN` | 手順 3 でコピーした長いトークン |
| `CLOUDFLARE_ACCOUNT_ID` | 手順 2 の Account ID |
| `CLOUDFLARE_PAGES_PROJECT_NAME` | 手順 1 で決めた Pages のプロジェクト名（例: `daily-brief-private`） |

保存後、**Actions** で **Daily brief** を **Run workflow** すると、ログに **Deploy to Cloudflare Pages** が走り、成功すれば Cloudflare 側に `dist/` が載ります。

---

## 5. Zero Trust（Access）で「自分だけ」にする

### 5-1. Zero Trust を有効にする（初回のみ）

1. [Cloudflare Zero Trust](https://one.dash.cloudflare.com/) にアクセス  
2. 初回はチーム名などを聞かれることがあります（無料枠で開始可能）。  
   - **「社内の VPN のようなもの」ではなく**、あくまで「この URL の前にログインを挟む」ためのダッシュボードだと思うと整理しやすいです。

### 5-2. アプリケーションを追加

1. 左メニュー **Access** → **Applications**  
2. **Add an application** → **Self-hosted**  
   - **Self-hosted**：自分が使っている **`〇〇.pages.dev` のような URL** に保護をかける設定です。  
3. **Application domain**  
   - **Subdomain**: 例 `daily-brief-private`（Pages のプロジェクト名と揃えると分かりやすい）  
   - **Domain**: `pages.dev` を選ぶ（または自分のカスタムドメイン）  
   → 結果として **`https://daily-brief-private.pages.dev`** のようなホストと一致させる  

4. **Policies（ポリシー）**  
   - **Include**: **Emails** → 自分のメールアドレスを追加  
   - 認証方法: **One-time PIN**（メールにコードが届く）が簡単  

5. 保存  

これで **ログインしていない人はページ本文を見られず**、ログインした許可メールだけ閲覧できます。

---

## 6. （重要）GitHub Pages を止めて「公開 URL」を無くす

Cloudflare だけにしたい場合、**GitHub Pages がまだ有効だと、公開 URL も更新され続けます**（＝「秘密の Cloudflare」と「誰でも見られる GitHub」の二系統になる）。

### 方法 A：GitHub の設定で Pages をオフ

**Settings** → **Pages** → **Build and deployment** で **None** にする（またはサイトを無効化）。

### 方法 B：ワークフローからデプロイを外す

[`.github/workflows/daily-brief.yml`](../.github/workflows/daily-brief.yml) から次を削除またはコメントアウト：

- `upload-pages-artifact@v3`（成果物を GitHub にアップロードする処理）  
- `deploy-pages@v4`（GitHub Pages へのデプロイ）  
- `environment: name: github-pages`（Cloudflare のみなら不要なことが多い）  

`.github/workflows/pages.yml` も **push のたびに公開する**ので、非公開運用なら **無効化**またはファイル削除を検討してください。

---

## 7. トラブルシュート

| 現象 | 確認すること |
|------|----------------|
| Cloudflare デプロイがスキップされる | 3 つの Secret がすべて設定されているか |
| Access 後もすぐ見える | アプリのドメインが **実際の Pages URL** と一致しているか（タイプミスが多いです） |
| 403 / デプロイ失敗 | トークンの権限に Pages Edit があるか |

---

## ローカルから手動デプロイ（お試し）

自分の PC から一度だけ試すときの例です（パスは環境に合わせてください）。

```powershell
cd "c:\Users\hirok\OneDrive\Desktop\My-Second-Project"
pip install -r requirements.txt
python -m brief_pipeline.build --mock
$env:CLOUDFLARE_API_TOKEN="（トークン）"
$env:CLOUDFLARE_ACCOUNT_ID="（アカウント ID）"
npx wrangler@3 pages deploy dist --project-name="（プロジェクト名）"
```

- **`npx`**：Node.js の仕組みで「この場限りでコマンドを実行する」イメージ。Wrangler をグローバルに入れなくても使えます。

---

## 参考

- [Wrangler CLI · Pages deploy](https://developers.cloudflare.com/workers/wrangler/commands/#deploy-2)
