from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from typing import Any

STATE_VERSION = 1


def default_state() -> dict[str, Any]:
    return {"version": STATE_VERSION, "dates": {}}


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return default_state()
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return default_state()
    if data.get("version") != STATE_VERSION:
        merged = default_state()
        merged["dates"] = data.get("dates") or {}
        return merged
    data.setdefault("dates", {})
    return data


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def record_brief_day(
    state: dict[str, Any],
    brief_date: str,
    topics: list[dict[str, Any]],
) -> dict[str, Any]:
    """同日は上書き。各トピックに topic_index を付与。"""
    st = deepcopy(state)
    st.setdefault("dates", {})
    normalized: list[dict[str, Any]] = []
    for i, t in enumerate(topics, start=1):
        row = dict(t)
        row["topic_index"] = i
        row.setdefault("share_record", "pending")
        normalized.append(row)
    st["dates"][brief_date] = normalized
    return st


def count_pending_all(state: dict[str, Any]) -> int:
    n = 0
    for _, topics in (state.get("dates") or {}).items():
        for t in topics:
            if t.get("share_record") == "pending":
                n += 1
    return n


def pending_backlog_rows(
    state: dict[str, Any],
    *,
    exclude_on_or_after: str | None = None,
    link_prefix: str = "./",
    limit: int = 30,
) -> list[dict[str, Any]]:
    """共有記録が pending のトピックを日付新しい順。exclude_on_or_after 以降の日付は除外（当日分をバックログから除く）。"""
    dates: dict[str, list] = state.get("dates") or {}
    rows: list[dict[str, Any]] = []
    for d in sorted(dates.keys(), reverse=True):
        if exclude_on_or_after and d >= exclude_on_or_after:
            continue
        parts = d.split("-")
        if len(parts) != 3:
            continue
        y, m, day = parts
        brief_path = f"{y}/{m}/{day}/index.html"
        for t in dates[d]:
            if t.get("share_record") != "pending":
                continue
            rows.append(
                {
                    "date_iso": d,
                    "title": t.get("title") or "",
                    "priority": t.get("priority") or "review",
                    "topic_index": int(t.get("topic_index") or 1),
                    "href": f"{link_prefix}{brief_path}#topic-{int(t.get('topic_index') or 1)}",
                }
            )
    return rows[:limit]


def monthly_shared_stats(
    state: dict[str, Any],
    *,
    months: int = 3,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """
    「共有した」確定のみを月別に集計。share_record が done_shared のもの。
    月キーはブリーフ日付の暦月（state を手動更新した場合に数字が入る MVP）。
    """
    today = today or date.today()
    dates: dict[str, list] = state.get("dates") or {}
    buckets: dict[str, dict[str, int]] = {}

    for d_str, topics in dates.items():
        try:
            d = datetime.strptime(d_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        key = f"{d.year:04d}-{d.month:02d}"
        for t in topics:
            if t.get("share_record") != "done_shared":
                continue
            b = buckets.setdefault(key, {"immediate": 0, "review": 0, "reference": 0})
            pr = t.get("priority") or "review"
            if pr in b:
                b[pr] += 1

    keys: list[str] = []
    y, mm = today.year, today.month
    for _ in range(months):
        keys.append(f"{y:04d}-{mm:02d}")
        mm -= 1
        if mm < 1:
            mm = 12
            y -= 1

    result: list[dict[str, Any]] = []
    for idx, key in enumerate(keys):
        counts = buckets.get(
            key, {"immediate": 0, "review": 0, "reference": 0}
        ).copy()
        imm, rev, ref = counts["immediate"], counts["review"], counts["reference"]
        total = imm + rev + ref
        year_month_label = f"{int(key[:4])}年{int(key[5:7])}月"
        pct_imm = pct_rev = pct_ref = 0.0
        if total > 0:
            pct_imm = round(100.0 * imm / total, 3)
            pct_rev = round(100.0 * rev / total, 3)
            pct_ref = round(100.0 * ref / total, 3)

        delta = None
        delta_cls = "text-emerald-700"
        if idx + 1 < len(keys):
            older_key = keys[idx + 1]
            older = buckets.get(
                older_key, {"immediate": 0, "review": 0, "reference": 0}
            )
            older_total = (
                older["immediate"] + older["review"] + older["reference"]
            )
            dlt = total - older_total
            delta = f"+{dlt}" if dlt >= 0 else str(dlt)
            if dlt < 0:
                delta_cls = "text-red-700"
            elif dlt == 0:
                delta_cls = "text-slate-600"

        result.append(
            {
                "year_month_key": key,
                "year_month_label": year_month_label,
                "total_shared": total,
                "shared_immediate": imm,
                "shared_review": rev,
                "shared_reference": ref,
                "pct_immediate": pct_imm,
                "pct_review": pct_rev,
                "pct_reference": pct_ref,
                "bar_title": f"即共有{imm}・要確認{rev}・参考{ref}",
                "delta_prev": delta,
                "delta_color_class": delta_cls,
            }
        )
    return result
