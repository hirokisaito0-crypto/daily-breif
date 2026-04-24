# Cloudflare Pages + Zero Trust（本人限定の Web 公開）

静的出力は [brief_pipeline/build.py](../brief_pipeline/build.py) が `dist/` に書き出します。GitHub Pages の公開 URL だけでは「URL を知っている第三者」に見られるリスクがあるため、**Cloudflare Access（Zero Trust）** で本人のメール（または IdP）だけに絞る構成を推奨します。

## 1. Pages プロジェクトを作る

1. [Cloudflare Dashboard](https://dash.cloudflare.com/) → **Workers & Pages** → **Create** → **Pages** → **Direct Upload** または Git 連携。
2. 初回はローカルで `dist/` を生成し、ZIP に固めてアップロードしてもよいです。

## 2. Wrangler CLI（任意）

```bash
npm i -g wrangler
wrangler login
cd path/to/My-Second-Project
pip install -r requirements.txt
python -m brief_pipeline.build --mock
npx wrangler pages deploy dist --project-name=YOUR_PROJECT_NAME
```

CI からデプロイする場合は `CLOUDFLARE_API_TOKEN` と `CLOUDFLARE_ACCOUNT_ID` を GitHub Secrets に登録し、`wrangler pages deploy dist` をワークフローに追加します（トークンは **Account · Cloudflare Pages · Edit** など最小権限）。

## 3. Access ポリシー（本人のみ）

1. Cloudflare Zero Trust ダッシュボード → **Access** → **Applications**。
2. **Add an application** → **Self-hosted**。
3. **Application domain** に Pages のホスト（例: `daily-brief.pages.dev` またはカスタムドメイン）を指定。
4. **Policy** で **Include** に自分のメール（または Google Workspace 等のグループ）を追加。**One-time PIN** でも可。
5. 保存後、未認証でアクセスするとログイン画面になり、許可された本人だけが `dist/index.html` を閲覧できます。

## 4. GitHub Actions との役割分担

- **Push 時**: [.github/workflows/pages.yml](../.github/workflows/pages.yml) は `--mock` で `dist/` を生成し、GitHub Pages へ載せる想定です（公開サイト向け）。非公開運用ではこのジョブを止めるか、プライベートリポジトリ＋アクセス制御された配信先に切り替えてください。
- **毎日英国 7 時付近**: [.github/workflows/daily-brief.yml](../.github/workflows/daily-brief.yml) はアーティファクトとして `dist/` を残します。ここから Wrangler で Pages にアップロードするステップを足すと、本番の非公開ブリーフに繋がります。

## 5. 代替案（短いメモ）

- **Netlify** のパスワード保護や **Netlify Identity**（プラン・設定による）。
- **S3 + CloudFront** と署名付き URL／Lambda@Edge による Basic 認証。
- **Vercel** のデプロイ保護（チーム機能）。
