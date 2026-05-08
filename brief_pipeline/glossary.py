from __future__ import annotations

import re
from typing import Iterable

# 頻出の略語・制度の固定辞書（最小セット）
# - term: 表示名（略語＋正式名を併記してもよい）
# - definition: 新卒でも分かる一言（です・ます調）
GLOSSARY: dict[str, tuple[str, str]] = {
    "FCA": (
        "FCA（Financial Conduct Authority）",
        "イギリスで投資・保険・融資などの金融サービスが、ルールに沿って提供されているかを監督する当局です。",
    ),
    "PRA": (
        "PRA（Prudential Regulation Authority）",
        "イングランド銀行の中で、銀行などが倒れにくいか（健全性）を監督する部門です。",
    ),
    "BOE": (
        "BoE（Bank of England）",
        "イングランド銀行の略で、英国の中央銀行です。金融政策や金融システムの安定にも関与します。",
    ),
    "EBA": (
        "EBA（European Banking Authority）",
        "EUの銀行規制・監督の基準づくりを担う機関です（技術基準やガイドライン等）。",
    ),
    "ESMA": (
        "ESMA（European Securities and Markets Authority）",
        "EUの証券・市場（投資家保護や市場の透明性など）に関する監督・基準づくりを担う機関です。",
    ),
    "ECB": (
        "ECB（European Central Bank）",
        "欧州中央銀行の略で、ユーロ圏の中央銀行です。金融政策に加え、銀行監督にも関与します。",
    ),
    "SSM": (
        "SSM（Single Supervisory Mechanism）",
        "ユーロ圏の大手銀行などを、ECBと各国当局が一体で監督する仕組みです。",
    ),
    "AML": (
        "AML（Anti-Money Laundering）",
        "犯罪収益の資金洗浄（マネーロンダリング）を防ぐための規制や業務プロセスのことです。",
    ),
    "SANCTIONS": (
        "制裁（Sanctions）",
        "特定の国・団体・個人との取引を禁止・制限するルールです。違反すると重い罰則の対象になり得ます。",
    ),
    "STRESS_TEST": (
        "ストレステスト（Stress test）",
        "悪い状況を想定して損失や資本の余裕を試し、金融機関が十分な体力かを見る分析です。",
    ),
    "OP_RESILIENCE": (
        "オペレーショナル・レジリエンス（Operational resilience）",
        "システム障害やサイバー攻撃が起きても、重要な業務を止めない／早く復旧するための取り組みです。",
    ),
    "THIRD_PARTY_RISK": (
        "第三者リスク（Third-party risk）",
        "クラウド事業者など外部委託先に依存することで生じる停止・情報漏えい等のリスクです。",
    ),
}


_TERM_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("FCA", re.compile(r"\bFCA\b", re.I)),
    ("PRA", re.compile(r"\bPRA\b", re.I)),
    ("BOE", re.compile(r"\bBoE\b|\bBank of England\b", re.I)),
    ("EBA", re.compile(r"\bEBA\b", re.I)),
    ("ESMA", re.compile(r"\bESMA\b", re.I)),
    ("ECB", re.compile(r"\bECB\b|\bEuropean Central Bank\b", re.I)),
    ("SSM", re.compile(r"\bSSM\b|\bsingle supervisory mechanism\b", re.I)),
    ("AML", re.compile(r"\bAML\b|anti[- ]money laundering", re.I)),
    ("SANCTIONS", re.compile(r"\bsanctions?\b|制裁", re.I)),
    ("STRESS_TEST", re.compile(r"stress test|ストレステスト", re.I)),
    ("OP_RESILIENCE", re.compile(r"operational resilience|レジリエンス", re.I)),
    ("THIRD_PARTY_RISK", re.compile(r"third[- ]party risk|第三者リスク", re.I)),
]


def extract_glossary_keys(texts: Iterable[str]) -> list[str]:
    hay = "\n".join([t for t in texts if isinstance(t, str) and t.strip()])
    found: list[str] = []
    if not hay:
        return found
    for key, pat in _TERM_PATTERNS:
        if pat.search(hay):
            found.append(key)
    return found


def build_terms_explained(keys: Iterable[str], *, limit: int = 5) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for k in keys:
        if k in seen:
            continue
        seen.add(k)
        if k not in GLOSSARY:
            continue
        term, definition = GLOSSARY[k]
        out.append({"term": term, "definition": definition})
        if len(out) >= limit:
            break
    return out

