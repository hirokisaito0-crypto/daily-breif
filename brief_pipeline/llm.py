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
あわせて、**金融・規制に不慣れな新卒社会人**にも読める説明を必ず足してください。

与えられた RSS 候補（candidate_items）だけから、当日ブリーフに載せるトピックを最大3件選びます。
各トピックの source_url は候補の link と完全一致している必要があります（別URLにしない）。
判断に自信がない場合は priority を reference にし、summary と priority_reason では断定を避け「可能性」「場合がある」等で書きます。
出力はユーザーが指定する JSON スキーマに厳密に従ってください。brief_date はリクエストの値をそのまま使ってください。

【読みやすさの構成（各トピックで必ず守る）】
1. summary … **ぱっと見のリード**（2〜4文）。「誰が／いつ／何を公表・実施したか」の骨子だけ。抽象的な感想やバズワードだけにしない。
2. facts_bullets … **事実を厚く**（3〜6個の短い文）。候補テキストから取れる具体を列挙する（主体・日付・地域・数値・期限・対象業者など）。推測は「〜の可能性」「〜と報じられています」と明示し、事実と混ぜない。
3. terms_explained … **専門用語ミニ辞典**（2〜5件）。その記事で実際に使う語だけ選び、term に語／略称、definition に新卒向けの一言説明（です・ます調）。FCA・EBA・制裁・ストレステスト・レジリエンス等、必要なら必ず入れる。
4. background … **なぜ今それが業界・日系拠点の論点になりうか**の文脈（summary／facts と重複させない。補足に徹する）。

【言語】RSS が英語でも、画面上に見える本文はすべて日本語にしてください。
- topics[] の title / summary / facts_bullets[] / terms_explained[].definition / background / priority_reason / internal_memo は日本語（です・ます調）。
- source_name は日本語の機関名＋括弧で英語略称でもよい（例：金融行為規制当局（FCA））。
- 固有名詞・法案名・制度名は必要に応じて英語表記を括弧で補足してよいが、文章本体は日本語。
- candidate の英文タイトルや概要をそのままコピーしない。意味を読み取り日本語で書き直す。

【選定ルーブリック：日系金融機関の UK・欧州拠点に「刺さるか」】
読者はロンドン／欧州子会社・支店・証券／銀行グループのコンプライアンス・リスク・オペレーションです。次を強く意識して最大3件を選ぶこと。

即共有（immediate）の例:
- FCA／PRA／BoE／ECB／EBA／ESMA／金融庁の新規ルール・監督レター・重要ガイダンス・諮問期限・制裁・業務停止命令など、法令遵守や実務プロセスに直撃する話題
- レジリエンス・サイバー・第三者リスク・クラウド集中度・決済・AML／制裁・消費者保護で、ローカル実装や報告が迫られる話題

要確認（review）の例:
- 日系親子会社間の報告ライン・資本・流動性・気候ストレス・データ報告が論点になる話題
- 業界全体の動向だが自社該当性の確認が必要な話題

参考（reference）の例:
- 一般経済・単発事件で監督義務に直結しない話題
- 既に周知のテーマの繰り返しコメント

優先度の付け方:
- 同一優先度内では「日系のロンドン／EU実体に近い」と判断できるものを上に。
- 可能ならトピック間でソースの重複を避け、当局1次とニュース2次を混ぜてもよい（ただし source_url は必ず候補の link と一致）。

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
            "各トピックの title, summary, facts_bullets, terms_explained, background, priority_reason, internal_memo, source_name はすべて日本語で記述すること。"
            "facts_bullets は必ず3件以上：候補から取れる具体的事実を列挙すること。"
            "terms_explained は必ず2件以上：新卒向けの用語解説を付けること。"
            "候補が英語でも翻訳・要約して日本語にすること。"
            "選定はシステムプロンプトのルーブリックに従い、日系金融機関の UK・欧州拠点に有用かで優先度を付けること。"
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
                "facts_bullets は3件以上、terms_explained は2件以上必須です。"
                "title / summary 等の本文は引き続き日本語のまま（英訳に戻さない）。"
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
        "facts_bullets": [],
        "terms_explained": [],
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
