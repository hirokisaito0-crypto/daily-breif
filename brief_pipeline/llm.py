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

重要:
- フィールド名を変えない（例: source_url を link にしない）
- 必須フィールドは省略しない（背景や社内メモが無い場合は空文字でもよい）
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
    data = _call_llm_once(
        client=client,
        model=model,
        system_prompt=SYSTEM_PROMPT,
        user_msg=user_msg,
        schema=schema,
        temperature=0.3,
    )

    data = _normalize_llm_output(data)
    try:
        jsonschema.validate(instance=data, schema=schema)
        _assert_source_urls_from_candidates(data, items)
        return data
    except Exception as e:
        # 失敗時は「スキーマに合わせて修復して」ともう一度依頼してから検証する
        log.warning("LLM output invalid, retrying with fix prompt: %s", e)
        fixed = _call_llm_once(
            client=client,
            model=model,
            system_prompt=(
                SYSTEM_PROMPT
                + "\nあなたの直前の出力がスキーマに一致しませんでした。"
                "候補RSSのlink以外のURLは使わず、必ずスキーマ通りのフィールド名・型で出力し直してください。"
            ),
            user_msg=json.dumps(
                {
                    "brief_date": brief_date,
                    "candidate_items": [i.as_llm_dict() for i in items],
                    "previous_output": data,
                    "fix_instructions": "スキーマに一致する JSON のみを返す。余計なキーは禁止。",
                },
                ensure_ascii=False,
            ),
            schema=schema,
            temperature=0.0,
        )
        fixed = _normalize_llm_output(fixed)
        jsonschema.validate(instance=fixed, schema=schema)
        _assert_source_urls_from_candidates(fixed, items)
        return fixed


def _call_llm_once(
    *,
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_msg: str,
    schema: dict[str, Any],
    temperature: float,
) -> dict[str, Any]:
    """
    OpenAI 側に JSON Schema を渡して構造化出力を強制する。
    サポートされないモデルの場合は json_object にフォールバック。
    """
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "daily_brief",
                    "schema": schema,
                    "strict": True,
                },
            },
        )
    except Exception as e:
        log.warning("json_schema response_format failed, falling back: %s", e)
        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
        )

    content = resp.choices[0].message.content or "{}"
    return json.loads(content)


def _normalize_llm_output(data: dict[str, Any]) -> dict[str, Any]:
    """
    LLM がスキーマと違うキー名を返す場合があるため、最小限の補正を行う。
    - source_url の代わりに link を返すケース: link → source_url へ移す
    - 必須フィールドの欠落: 空文字で埋める（MVP。意味が無い場合は空でよい）
    """
    if not isinstance(data, dict):
        return {"brief_date": "", "topics": []}

    topics = data.get("topics")
    if not isinstance(topics, list):
        data["topics"] = []
        return data

    required_defaults = {
        "priority": "review",
        "title": "",
        "summary": "",
        "source_name": "",
        "source_url": "",
        "published_date": "",
        "background": "",
        "priority_reason": "",
        "client_share": "judgment",
        "share_record": "pending",
        "internal_memo": "",
    }

    normalized: list[dict[str, Any]] = []
    for t in topics:
        if not isinstance(t, dict):
            continue
        row = dict(required_defaults)
        row.update(t)
        # alias: link -> source_url
        if (not row.get("source_url")) and row.get("link"):
            row["source_url"] = row.get("link")
        row.pop("link", None)
        normalized.append(row)

    data["topics"] = normalized[:3]
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
