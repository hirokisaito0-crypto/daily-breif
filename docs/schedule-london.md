# 英国ローカル 07:00 トリガー

## 採用した方式（GitHub Actions）

[.github/workflows/daily-brief.yml](../.github/workflows/daily-brief.yml) は UTC の `cron` を **1 日 2 本**（`0 6 * * *` と `0 7 * * *`）登録し、ジョブ開始時に **Europe/London の現在時刻が 7 時台か** を Python で判定します。

- **冬（GMT）**: ロンドン 07:00 は UTC 07:00 → `0 7` のジョブだけが `hour == 7` でビルド実行。
- **夏（BST）**: ロンドン 07:00 は UTC 06:00 → `0 6` のジョブだけが実行。

`workflow_dispatch` のときは時刻に関係なく常にビルドします（手動検証用）。

## より厳密にしたい場合

- **Google Cloud Scheduler** / **AWS EventBridge** で `timezone: Europe/London` を指定し、**Cloud Run Job** や **Lambda** を 1 本の cron にする。
- 自宅 **VPS + systemd timer** で `OnCalendar=Europe/London:07:00`。

GitHub Actions のみで夏冬を自動追従するのは難しいため、上記の **2 本 cron + ゲート** がコストと実装のバランスが良い妥協案です。
