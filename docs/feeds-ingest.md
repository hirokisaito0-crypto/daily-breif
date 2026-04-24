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
