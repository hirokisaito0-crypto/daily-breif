# LLM 構造化出力と HTML フィールドの対応

OpenAI Chat Completions（`response_format: json_object`）で返させる JSON は [schemas/brief-output.schema.json](../schemas/brief-output.schema.json) で検証します。検証後、[brief_pipeline/build.py](../brief_pipeline/build.py) で `share_record` を常に `pending` に揃え（自動生成 MVP）、[brief_pipeline/render_context.py](../brief_pipeline/render_context.py) で Jinja 向けの表示用フィールドを付与します。

## スキーマ → 画面

| JSON フィールド | 意味 | テンプレート上の扱い |
|----------------|------|---------------------|
| `brief_date` | ブリーフの暦日（`YYYY-MM-DD`、Europe/London） | `<time datetime>` とフッター |
| `topics[]` | 最大 3 件 | ヘッダ一覧・本文カード |
| `topics[].priority` | `immediate` / `review` / `reference` | 即共有・要確認・参考のバッジ色・帯色 |
| `topics[].title` | 見出し | h2・一覧 |
| `topics[].summary` | 要約 | 要約ブロック |
| `topics[].source_name` | 出典の表示名 | 出典ラベル |
| `topics[].source_url` | 出典 URL | **候補 RSS の `link` と完全一致必須**（ハルシネーション防止） |
| `topics[].published_date` | 公表日 | 公表日 |
| `topics[].background` | 背景 | 背景 |
| `topics[].priority_reason` | 優先度の理由 | 色付き理由ボックス |
| `topics[].client_share` | `recommended` / `judgment` / `not_recommended` | 推奨・要判断・非推奨バッジ |
| `topics[].share_record` | LLM 値は無視し `pending` で上書き | ラジオ初期選択（Phase2 で永続化予定） |
| `topics[].internal_memo` | 空文字なら非表示 | 社内メモブロック |

## 優先度ソート

`immediate` → `review` → `reference` の順に並べ替えたうえで `topic_index`（`#topic-1` 等）を振ります。`data/state.json` のバックログリンクと一致させるため、[brief_pipeline/build.py](../brief_pipeline/build.py) では **ソート後** に `record_brief_day` へ渡します。

## プロンプトの要点

[brief_pipeline/llm.py](../brief_pipeline/llm.py) のシステムプロンプトで次を固定しています。

- 読者は英国・欧州の日系金融機関担当であること。
- **候補アイテム以外の URL を出典にしないこと**（検証で失敗します）。
- 断定を避け、監督上の「可能性」を明示すること。

## モデル

既定は `gpt-4o-mini`（`python -m brief_pipeline.build --model ...` で変更）。
