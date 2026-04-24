from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

PRIORITY_ORDER = ("immediate", "review", "reference")
PRIORITY_LABEL_JA = {
    "immediate": "即共有",
    "review": "要確認",
    "reference": "参考",
}
PRIORITY_BADGE_ROW = {
    "immediate": {
        "summary_row_ring": "ring-red-100",
        "summary_badge_bg": "bg-red-50",
        "summary_badge_text": "text-red-800",
        "summary_badge_ring": "ring-red-200",
        "summary_dot": "bg-red-500",
    },
    "review": {
        "summary_row_ring": "ring-amber-100",
        "summary_badge_bg": "bg-amber-50",
        "summary_badge_text": "text-amber-950",
        "summary_badge_ring": "ring-amber-200",
        "summary_dot": "bg-amber-400",
    },
    "reference": {
        "summary_row_ring": "ring-emerald-100",
        "summary_badge_bg": "bg-emerald-50",
        "summary_badge_text": "text-emerald-800",
        "summary_badge_ring": "ring-emerald-200",
        "summary_dot": "bg-emerald-500",
    },
}
ARTICLE_SIDEBAR = {
    "immediate": {
        "article_sidebar_border": "border-red-100",
        "article_sidebar_bg": "bg-red-50",
        "article_dot": "text-red-500",
        "article_sidebar_label": "text-red-700",
        "article_sidebar_title": "text-red-900",
    },
    "review": {
        "article_sidebar_border": "border-amber-100",
        "article_sidebar_bg": "bg-amber-50",
        "article_dot": "text-amber-500",
        "article_sidebar_label": "text-amber-800",
        "article_sidebar_title": "text-amber-950",
    },
    "reference": {
        "article_sidebar_border": "border-emerald-100",
        "article_sidebar_bg": "bg-emerald-50",
        "article_dot": "text-emerald-500",
        "article_sidebar_label": "text-emerald-800",
        "article_sidebar_title": "text-emerald-950",
    },
}
REASON_BOX = {
    "immediate": {
        "reason_box_bg": "bg-red-50/80",
        "reason_box_ring": "ring-red-100",
        "reason_dt": "text-red-800",
        "reason_dd": "text-red-950",
    },
    "review": {
        "reason_box_bg": "bg-amber-50/90",
        "reason_box_ring": "ring-amber-100",
        "reason_dt": "text-amber-900",
        "reason_dd": "text-amber-950",
    },
    "reference": {
        "reason_box_bg": "bg-emerald-50/90",
        "reason_box_ring": "ring-emerald-100",
        "reason_dt": "text-emerald-900",
        "reason_dd": "text-emerald-950",
    },
}


def _weekday_ja(d) -> str:
    w = "月火水木金土日"
    return w[d.weekday()]


def format_date_display_ja(iso_date: str) -> str:
    from datetime import datetime

    d = datetime.strptime(iso_date, "%Y-%m-%d").date()
    return f"{d.year}年{d.month}月{d.day}日（{_weekday_ja(d)}）"


def sort_topics(topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(t: dict[str, Any]) -> tuple[int, int]:
        pr = t.get("priority") or "review"
        try:
            pi = PRIORITY_ORDER.index(pr)
        except ValueError:
            pi = 99
        return (pi, 0)

    return sorted(topics, key=key)


def enrich_topics(topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tier_count: dict[str, int] = {p: 0 for p in PRIORITY_ORDER}
    out: list[dict[str, Any]] = []
    for i, raw in enumerate(sort_topics(topics), start=1):
        pr = raw.get("priority") or "review"
        if pr not in PRIORITY_ORDER:
            pr = "review"
        tier_count[pr] += 1
        cs = raw.get("client_share") or "judgment"
        if cs == "recommended":
            csl, csc, csn = "推奨", "bg-emerald-100 text-emerald-900 ring-emerald-200", ""
        elif cs == "not_recommended":
            csl, csc, csn = "非推奨", "bg-slate-200 text-slate-800 ring-slate-300", "（社内ナレッジ向け）"
        else:
            csl, csc, csn = "要判断", "bg-amber-100 text-amber-950 ring-amber-200", ""

        row = dict(raw)
        row["topic_index"] = i
        row["priority_label"] = PRIORITY_LABEL_JA.get(pr, "要確認")
        row["priority_index"] = tier_count[pr]
        row["summary_row_ring"] = PRIORITY_BADGE_ROW[pr]["summary_row_ring"]
        row["summary_badge_bg"] = PRIORITY_BADGE_ROW[pr]["summary_badge_bg"]
        row["summary_badge_text"] = PRIORITY_BADGE_ROW[pr]["summary_badge_text"]
        row["summary_badge_ring"] = PRIORITY_BADGE_ROW[pr]["summary_badge_ring"]
        row["summary_dot"] = PRIORITY_BADGE_ROW[pr]["summary_dot"]
        row.update(ARTICLE_SIDEBAR[pr])
        row.update(REASON_BOX[pr])
        row["client_share_label"] = csl
        row["client_share_classes"] = csc
        row["client_share_note"] = csn
        out.append(row)
    return out


def pending_rows_for_template(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    badge = {
        "immediate": "bg-red-50 text-red-800 ring-red-100",
        "review": "bg-amber-50 text-amber-950 ring-amber-100",
        "reference": "bg-emerald-50 text-emerald-800 ring-emerald-100",
    }
    out = []
    for r in rows:
        pr = r.get("priority") or "review"
        out.append(
            {
                **r,
                "priority_label": PRIORITY_LABEL_JA.get(pr, "要確認"),
                "priority_badge_classes": badge.get(pr, badge["review"]),
            }
        )
    return out


def render_html(
    *,
    repo_root: Path,
    context: dict[str, Any],
) -> str:
    env = Environment(
        loader=FileSystemLoader(str(repo_root / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tpl = env.get_template("daily-brief.j2.html")
    return tpl.render(**context)
