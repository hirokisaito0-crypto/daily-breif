# Daily brief（日系金融機関 UK・欧州向け）

リポジトリには次の二系統があります。

- **ルートの [`index.html`](index.html)**  
  手で触るレイアウトサンプル（Surge サンプルと同系）。デザイン確認・コピー用。
- **自動生成パイプライン**  
  RSS →（任意で）OpenAI → Jinja テンプレ → **`dist/`** に静的サイトを出力。

本番のホスティングは **`dist/`** を公開してください（[`netlify.toml`](netlify.toml)・[GitHub Pages ワークフロー](.github/workflows/pages.yml) は `dist` 向けに設定済み）。

## ローカルでビルドする

Python 3.12 推奨（3.11 でも可）。

```powershell
cd "c:\Users\hirok\OneDrive\Desktop\My-Second-Project"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

- **レイアウトだけ確認（API 不要）**  
  `python -m brief_pipeline.build --mock`  
  → `dist/index.html` と `dist/年/月/日/index.html` が出力されます。`data/state.json` が無ければ作成されます（`.gitignore` で除外）。
- **RSS + OpenAI で本番相当**  
  環境変数 `OPENAI_API_KEY` を設定し、`python -m brief_pipeline.build`  
  → 出典 URL は候補 RSS の `link` と完全一致する必要があります（[`brief_pipeline/llm.py`](brief_pipeline/llm.py)）。

オプションは `python -m brief_pipeline.build --help` を参照。

## 設定ファイル

| パス | 内容 |
|------|------|
| [`brief_pipeline/config/feeds.yaml`](brief_pipeline/config/feeds.yaml) | 当局 RSS ホワイトリスト |
| [`schemas/brief-output.schema.json`](schemas/brief-output.schema.json) | LLM 出力 JSON スキーマ |
| [`templates/daily-brief.j2.html`](templates/daily-brief.j2.html) | 日次 HTML テンプレート |
| [`data/state.example.json`](data/state.example.json) | `state.json` の例（バックログ／月次用） |

ドキュメント: [docs/feeds-ingest.md](docs/feeds-ingest.md) · [docs/llm-mapping.md](docs/llm-mapping.md) · [docs/schedule-london.md](docs/schedule-london.md) · [docs/operations.md](docs/operations.md) · [docs/cloudflare-pages-access.md](docs/cloudflare-pages-access.md) · [docs/phase2-kv-api.md](docs/phase2-kv-api.md)

## GitHub Actions

| ワークフロー | 役割 |
|--------------|------|
| [`.github/workflows/pages.yml`](.github/workflows/pages.yml) | `main` / `master` への push で `pip install` → `build --mock` → **GitHub Pages** に `dist/` をデプロイ。`data/state.json` はブランチ単位でキャッシュ。 |
| [`.github/workflows/daily-brief.yml`](.github/workflows/daily-brief.yml) | 毎日 UTC 6:00 / 7:00 の 2 本で起動し、**Europe/London が 7 時のときだけ**ビルド。`OPENAI_API_KEY` が無い場合は `--mock`。**GitHub Pages** にも載せ、任意で **Cloudflare Pages**（Secrets: `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ACCOUNT_ID` / `CLOUDFLARE_PAGES_PROJECT_NAME`）。Artifacts にも `dist/` を 14 日保持。 |

非公開 URL には GitHub Pages 単体では足りないことが多いです。**Cloudflare Pages + Access** などの手順は [docs/cloudflare-pages-access.md](docs/cloudflare-pages-access.md) を参照してください。

## 他の人に見せる方法（短縮）

### A. GitHub Pages

1. リポジトリを GitHub に push。  
2. **Settings → Pages** で **Source: GitHub Actions**。  
3. 上記 `pages.yml` により `dist/` がデプロイされる。

### B. Netlify

Git 連携または CLI。`netlify.toml` の `command` で `dist/` をビルドします。ドラッグ＆ドロップする場合は、先にローカルで `python -m brief_pipeline.build --mock` して **`dist` フォルダだけ**をアップロードしてください。

### C. ローカルプレビュー

```powershell
npx --yes serve dist
```
