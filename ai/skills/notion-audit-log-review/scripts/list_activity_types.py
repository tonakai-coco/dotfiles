# -*- coding: utf-8 -*-
"""Notion 監査ログ CSV のアクティビティ種別を棚卸しする。

Usage:
    python list_activity_types.py <csv_path> [--top-actor-n 3] [--sample-desc-n 1]

stdout に JSON を出力する。LLM がこれを読んで観点定義を組む。
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))


def to_jst(ts_utc: str):
    try:
        return datetime.fromisoformat(ts_utc.replace("Z", "+00:00")).astimezone(JST)
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--top-actor-n", type=int, default=3, help="種別ごとに上位アクターを何件返すか")
    ap.add_argument("--sample-desc-n", type=int, default=1, help="種別ごとに代表説明文を何件返すか")
    args = ap.parse_args()

    etype_count: Counter = Counter()
    etype_actor: dict[str, Counter] = defaultdict(Counter)
    etype_desc: dict[str, list[str]] = defaultdict(list)
    etype_country: dict[str, Counter] = defaultdict(Counter)

    total_rows = 0
    period_min: datetime | None = None
    period_max: datetime | None = None
    actor_count: Counter = Counter()
    country_count: Counter = Counter()

    with open(args.csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for d in reader:
            total_rows += 1
            etype = d.get("アクティビティ種別", "")
            actor = d.get("件名", "")
            desc = d.get("アクティビティ", "")
            country = d.get("国", "")
            ts = to_jst(d.get("日付と時刻（UTC）", ""))

            etype_count[etype] += 1
            etype_actor[etype][actor] += 1
            etype_country[etype][country] += 1
            actor_count[actor] += 1
            country_count[country] += 1
            if len(etype_desc[etype]) < args.sample_desc_n and desc:
                etype_desc[etype].append(desc)

            if ts:
                if period_min is None or ts < period_min:
                    period_min = ts
                if period_max is None or ts > period_max:
                    period_max = ts

    types = []
    for et, n in etype_count.most_common():
        types.append({
            "etype": et,
            "count": n,
            "top_actors": [
                {"actor": a, "count": c}
                for a, c in etype_actor[et].most_common(args.top_actor_n)
            ],
            "top_countries": [
                {"country": c, "count": cnt}
                for c, cnt in etype_country[et].most_common(args.top_actor_n)
            ],
            "sample_descriptions": etype_desc[et],
        })

    out = {
        "csv_path": args.csv_path,
        "total_rows": total_rows,
        "unique_etype_count": len(etype_count),
        "period_jst": {
            "start": period_min.strftime("%Y-%m-%d %H:%M") if period_min else None,
            "end": period_max.strftime("%Y-%m-%d %H:%M") if period_max else None,
        },
        "unique_actor_count": len(actor_count),
        "top_actors_overall": [
            {"actor": a, "count": c} for a, c in actor_count.most_common(10)
        ],
        "country_distribution": [
            {"country": c, "count": cnt} for c, cnt in country_count.most_common()
        ],
        "activity_types": types,
    }

    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
