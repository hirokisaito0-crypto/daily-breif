from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import jsonschema

from brief_pipeline.ingest import fetch_feed_items
from brief_pipeline.llm import build_user_message, call_llm, load_fixture, load_schema
from brief_pipeline.render_context import (
    enrich_topics,
    format_date_display_ja,
    pending_rows_for_template,
    render_html,
    sort_topics,
)
from brief_pipeline.state import (
    count_pending_all,
    load_state,
    monthly_shared_stats,
    pending_backlog_rows,
    record_brief_day,
    save_state,
)

log = logging.getLogger("brief_pipeline.build")

REPO_ROOT = Path(__file__).resolve().parents[1]
FEEDS_PATH = REPO_ROOT / "brief_pipeline" / "config" / "feeds.yaml"
FIXTURE_PATH = REPO_ROOT / "brief_pipeline" / "fixtures" / "mock_llm_output.json"
LLM_MAX_CANDIDATES = 25


def _brief_date_london(now: datetime | None = None) -> str:
    now = now or datetime.now(ZoneInfo("Europe/London"))
    return now.date().isoformat()


def _write_outputs(html: str, brief_date: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    parts = brief_date.split("-")
    if len(parts) == 3:
        y, m, d = parts
        arch = out_dir / y / m / d
        arch.mkdir(parents=True, exist_ok=True)
        (arch / "index.html").write_text(html, encoding="utf-8")


def run(
    *,
    mock: bool,
    brief_date: str | None,
    out_dir: Path,
    state_path: Path,
    link_prefix: str,
    skip_ingest: bool,
    model: str,
) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    brief_date = brief_date or _brief_date_london()
    schema = load_schema(REPO_ROOT)

    if mock:
        llm_out = load_fixture(FIXTURE_PATH)
        llm_out["brief_date"] = brief_date
        items = []
    elif skip_ingest:
        items = []
        llm_out = {"brief_date": brief_date, "topics": []}
    else:
        items = fetch_feed_items(FEEDS_PATH)
        log.info("ingested %s candidate items", len(items))
        if not items:
            log.warning("no RSS items; writing empty brief")
            llm_out = {"brief_date": brief_date, "topics": []}
        else:
            if len(items) > LLM_MAX_CANDIDATES:
                log.info("capping candidates %s -> %s for LLM", len(items), LLM_MAX_CANDIDATES)
                items = items[:LLM_MAX_CANDIDATES]
            try:
                llm_out = call_llm(
                    brief_date=brief_date,
                    items=items,
                    schema=schema,
                    model=model,
                )
            except Exception as e:
                log.exception("LLM failed; falling back to empty brief: %s", e)
                llm_out = {"brief_date": brief_date, "topics": []}

    llm_out["brief_date"] = brief_date
    jsonschema.validate(instance=llm_out, schema=schema)

    topics_raw = sort_topics(list(llm_out.get("topics") or []))
    for t in topics_raw:
        t["share_record"] = "pending"

    state = load_state(state_path)
    new_state = record_brief_day(state, brief_date, topics_raw)
    save_state(state_path, new_state)

    topics = enrich_topics(topics_raw)
    pending_rows = pending_rows_for_template(
        pending_backlog_rows(
            new_state,
            exclude_on_or_after=brief_date,
            link_prefix=link_prefix,
        )
    )

    ctx = {
        "date_iso": brief_date,
        "date_display_ja": format_date_display_ja(brief_date),
        "topics": topics,
        "pending_count": count_pending_all(new_state),
        "pending_backlog": pending_rows,
        "monthly_stats": monthly_shared_stats(new_state, months=3),
    }
    html = render_html(repo_root=REPO_ROOT, context=ctx)
    _write_outputs(html, brief_date, out_dir)
    log.info("wrote %s and archive for %s", out_dir / "index.html", brief_date)

    if not mock and items:
        log.debug("user message size %s chars", len(build_user_message(brief_date, items)))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Build daily brief HTML into dist/.")
    p.add_argument("--mock", action="store_true", help="Use fixture JSON instead of RSS+LLM.")
    p.add_argument("--date", dest="brief_date", help="Brief date YYYY-MM-DD (default: Europe/London today).")
    p.add_argument("--out-dir", type=Path, default=REPO_ROOT / "dist", help="Output directory.")
    p.add_argument(
        "--state-path",
        type=Path,
        default=REPO_ROOT / "data" / "state.json",
        help="Persistent JSON for backlog / monthly stats.",
    )
    p.add_argument(
        "--link-prefix",
        default="./",
        help="Prefix for backlog hrefs (e.g. ./ or https://example.com/).",
    )
    p.add_argument(
        "--skip-ingest",
        action="store_true",
        help="With --mock off, skip RSS and emit empty topics (for dry runs).",
    )
    p.add_argument("--model", default="gpt-4o-mini", help="OpenAI model id.")
    args = p.parse_args(argv)

    return run(
        mock=args.mock,
        brief_date=args.brief_date,
        out_dir=args.out_dir.resolve(),
        state_path=args.state_path.resolve(),
        link_prefix=args.link_prefix,
        skip_ingest=args.skip_ingest,
        model=args.model,
    )


if __name__ == "__main__":
    raise SystemExit(main())
