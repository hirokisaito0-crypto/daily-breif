from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import jsonschema
from openai import OpenAI

from brief_pipeline.ingest import FeedItem

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """あなたは欧州・英国の金融監督・市場インフラに詳しいリサーチアシスタントです。
読者はイギリスおよび欧州で事業する日系金融機関のコンプライアンス・リスク・オペレーション担当です。

与えられた RSS 候補（candidate_items）だけから、当日ブリーフに載せるトピックを最大3件選びます。
各トピックの source_url は候補の link と完全一致している必要があります（別URLにしない）。
判断に自信がない場合は priority を reference にし、summary と priority_reason では断定を避け「可能性」「場合がある」等で書きます。
出力はユーザーが指定する JSON スキーマに厳密に従ってください。brief_date はリクエストの値をそのまま使ってください。
"""


def load_schema(repo_root: Path) -> dict[str, Any]:
    p = repo_root / "schemas" / "brief-output.schema.json"
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def build_user_message(brief_date: str, items: list[FeedItem]) -> str:
    payload = {
        "brief_date": brief_date,
        "candidate_items": [i.as_llm_dict() for i in items],
        "instructions": (
            "topics は最大3件。優先度順に並べること（immediate → review → reference）。"
            "該当する重要トピックが無ければ topics は空配列でもよい。"
        ),
    }
    return json.dumps(payload, ensure_ascii=False)


def call_llm(
    *,
    brief_date: str,
    items: list[FeedItem],
    schema: dict[str, Any],
    model: str = "gpt-4o-mini",
) -> dict[str, Any]:
    client = OpenAI()
    user_msg = build_user_message(brief_date, items)
    resp = client.chat.completions.create(
        model=model,
        temperature=0.3,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content or "{}"
    data = json.loads(content)
    jsonschema.validate(instance=data, schema=schema)
    _assert_source_urls_from_candidates(data, items)
    return data


def _assert_source_urls_from_candidates(data: dict[str, Any], items: list[FeedItem]) -> None:
    links = {i.link for i in items}
    for t in data.get("topics") or []:
        url = t.get("source_url")
        if url not in links:
            raise ValueError(f"LLM returned source_url not in candidates: {url!r}")


def load_fixture(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)
