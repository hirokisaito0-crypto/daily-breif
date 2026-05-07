# RSS インジェスト（MVP）

ホワイトリストは [brief_pipeline/config/feeds.yaml](../brief_pipeline/config/feeds.yaml) に集約しています。各エントリは `id`（安定キー）、`title`（出典表示のヒント）、`url`（RSS または Atom）です。

## 正規化

[brief_pipeline/ingest.py](../brief_pipeline/ingest.py) が次を行います。

- `httpx` で取得し、`feedparser` でパース。
- エントリごとに `title` / `link` / 要約（HTML タグ除去）/ 公開日時（`published` / `updated`）を抽出。
- `ingest.max_item_age_hours` より古い（UTC 基準）アイテムは捨てる。日付不明は取り込む。
- `link` が重複する場合は先勝ち。
- 取得失敗したフィードはログに警告してスキップ（他フィードは継続）。

## 運用メモ

- 各サイトの利用条件を確認し、**RSS が提供されている範囲**で運用してください。
- 403 になる場合は `User-Agent` やレートを調整するか、当局の別エンドポイント（公式 Atom）に差し替えてください。

## Google News RSS（検索フィード）

`feeds.yaml` に **Google News の検索結果 RSS** を追加できます（`q=` の検索語を編集）。

- **長所**: 当局以外の話題（報道・解説）も拾える  
- **注意**: 記事の `link` が **`news.google.com` のリダイレクト**になることがあります。そのURLは候補としてそのまま LLM に渡るため、`source_url` も同一文字列に一致させる必要があります（現行ロジックどおり）。
- **ノイズ対策**: 検索語を絞る、`ingest.max_entries_per_feed` を下げる、または検索用フィードの `id` を分けて後から削除しやすくする。

## Big4・コンサル等の公式フィード

Deloitte / PwC / EY / KPMG は **地域・サービス線ごとに RSS の有無と URL がバラバラ**です。**Deloitte** を例にすると、[blogs.deloitte.co.uk](https://blogs.deloitte.co.uk/) などチャネルごとに RSS が分かれていることが多いので、公式の「RSS」「Subscribe」「Insights」から **実際に XML が返る URL** を確認してから `feeds.yaml` に `id` と `url` を1行追加してください。

追加後は Actions の **Build brief** ログで `feed fetch failed` が無いか確認します。
