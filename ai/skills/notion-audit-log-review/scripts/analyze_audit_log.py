# -*- coding: utf-8 -*-
"""Notion 監査ログ CSV を観点定義 JSON に基づいて集計し、
audit-summary.md と audit-summary.json を出力する。

Usage:
    python analyze_audit_log.py <csv_path> --config <config.json> --out-dir <dir>
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

JST = timezone(timedelta(hours=9))

DEFAULT_SYSTEM_ACTORS = ["Notion App", "Notion AI", "Automation", "Notion Calendar"]
DEFAULT_DOMESTIC = ["JP"]
NON_FOREIGN_COUNTRY_TOKENS = {"", "不明", "N/A"}


def to_jst(ts_utc: str):
    try:
        return datetime.fromisoformat(ts_utc.replace("Z", "+00:00")).astimezone(JST)
    except Exception:
        return None


def fmt_ts(t):
    return t.strftime("%Y-%m-%d %H:%M") if t else "-"


def short(s, n=80):
    s = (s or "").replace("|", "/").replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def load_config(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg.setdefault("perspectives", [])
    cfg.setdefault("critical_etypes", [])
    cfg.setdefault("system_actors", DEFAULT_SYSTEM_ACTORS)
    cfg.setdefault("night_etypes", [])
    cfg.setdefault("burst", {"etype": "ページを閲覧", "per_minute": 100, "per_5min": 300})
    cfg.setdefault("domestic_country_codes", DEFAULT_DOMESTIC)
    cfg.setdefault("login_etype", "ログイン")
    return cfg


def analyze(csv_path: str, cfg: dict[str, Any]) -> dict[str, Any]:
    target_etypes = {et for p in cfg["perspectives"] for et in p["etypes"]}
    system_actors = set(cfg["system_actors"])
    domestic = set(cfg["domestic_country_codes"])
    burst_etype = cfg["burst"]["etype"]
    burst_pm = cfg["burst"]["per_minute"]
    burst_5m = cfg["burst"]["per_5min"]
    night_etypes = set(cfg["night_etypes"])
    login_etype = cfg["login_etype"]

    target_rows: list[dict[str, Any]] = []
    all_etype_ct: Counter = Counter()
    burst_ts_by_user: dict[str, list[datetime]] = defaultdict(list)
    total_rows = 0
    period_min: datetime | None = None
    period_max: datetime | None = None

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for d in csv.DictReader(f):
            total_rows += 1
            et = d.get("アクティビティ種別", "")
            all_etype_ct[et] += 1
            ts = to_jst(d.get("日付と時刻（UTC）", ""))
            user = d.get("件名", "")
            email = d.get("メールアドレス", "")
            country = d.get("国", "")

            if ts:
                if period_min is None or ts < period_min:
                    period_min = ts
                if period_max is None or ts > period_max:
                    period_max = ts

            if et == burst_etype and ts and user not in system_actors:
                burst_ts_by_user[email or user].append(ts)

            if et in target_etypes:
                target_rows.append({
                    "user": user,
                    "email": email,
                    "role": d.get("ステータス", ""),
                    "etype": et,
                    "edesc": d.get("アクティビティ", ""),
                    "audience": d.get("オーディエンス", ""),
                    "ts": ts,
                    "ip": d.get("IPアドレス", ""),
                    "country": country,
                    "platform": d.get("プラットフォーム", ""),
                    "mcp": d.get("MCPリダイレクトURL", ""),
                })

    # バースト検出
    bursts = []
    for u, lst in burst_ts_by_user.items():
        lst.sort()
        n = len(lst)
        m1 = m5 = 0
        j = 0
        for i in range(n):
            while lst[j] < lst[i] - timedelta(minutes=1):
                j += 1
            m1 = max(m1, i - j + 1)
        j = 0
        for i in range(n):
            while lst[j] < lst[i] - timedelta(minutes=5):
                j += 1
            m5 = max(m5, i - j + 1)
        if m1 >= burst_pm or m5 >= burst_5m:
            bursts.append({"user": u, "max_per_minute": m1, "max_per_5min": m5, "total": n})
    bursts.sort(key=lambda x: -x["max_per_minute"])

    foreign_logins = [
        r for r in target_rows
        if r["etype"] == login_etype
        and r["country"] not in domestic
        and r["country"] not in NON_FOREIGN_COUNTRY_TOKENS
    ]

    night_rows = [
        r for r in target_rows
        if r["ts"] and (r["ts"].hour >= 22 or r["ts"].hour < 6)
        and r["etype"] in night_etypes
        and r["user"] not in system_actors
    ]

    critical_rows = [r for r in target_rows if r["etype"] in cfg["critical_etypes"]]

    return {
        "csv_path": csv_path,
        "total_rows": total_rows,
        "all_etype_count": dict(all_etype_ct),
        "target_etypes": sorted(target_etypes),
        "period_jst": {
            "start": fmt_ts(period_min),
            "end": fmt_ts(period_max),
        },
        "target_rows": target_rows,
        "critical_rows": critical_rows,
        "bursts": bursts,
        "foreign_logins": foreign_logins,
        "night_rows": night_rows,
    }


def render_compact(rows: list[dict], w, max_n: int | None = None) -> None:
    if not rows:
        w("該当なし。\n\n")
        return
    n = len(rows)
    if max_n and n > max_n:
        w(f"全 {n} 件のうち上位 {max_n} 件を抜粋。\n\n")
        rows = rows[:max_n]
    w("| # | 日時(JST) | 実行者 | ロール | IP / 国 | 種別 | 内容 |\n")
    w("|---:|---|---|---|---|---|---|\n")
    for i, r in enumerate(rows, 1):
        ip_country = f"{r['ip']} ({r['country']})"
        w(f"| {i} | {fmt_ts(r['ts'])} | {short(r['user'],28)} | {r['role']} | {ip_country} | {r['etype']} | {short(r['edesc'],55)} |\n")
    w("\n")


def render_markdown(result: dict, cfg: dict) -> str:
    import io
    out = io.StringIO()
    w = out.write

    target_rows = result["target_rows"]
    critical_rows = result["critical_rows"]
    bursts = result["bursts"]
    foreign_logins = result["foreign_logins"]
    night_rows = result["night_rows"]
    perspectives = cfg["perspectives"]

    target_etypes_set = set(result["target_etypes"])

    w("# Notion 監査ログ サマリーレポート\n\n")
    w(f"- 対象 CSV: `{os.path.basename(result['csv_path'])}`\n")
    w(f"- 期間 (JST): {result['period_jst']['start']} 〜 {result['period_jst']['end']}\n")
    w(f"- 全イベント数: **{result['total_rows']:,}** / うち監査対象として抽出: **{len(target_rows):,}** 件\n")
    w(f"- 抽出対象アクティビティ種別: {len(target_etypes_set)} 種 / 除外: {len(result['all_etype_count']) - len(target_etypes_set)} 種\n\n")

    # §0 一行所感
    w("## 0. 一行所感\n\n")
    w(
        f"監査対象の **{len(target_rows):,}** 件のうち、最優先で確認すべき重大イベントは **{len(critical_rows)} 件**。"
        f"夜間 (JST 22:00–06:00) のリスク操作は **{len(night_rows)} 件**、"
        f"国外 IP からのログインは **{len(foreign_logins)} 件**、"
        f"閲覧バースト検出は **{len(bursts)} ユーザ** でした。"
        f"観点別の内訳と詳細は以下の §1〜§6 を参照。\n\n"
    )

    # §1 観点別件数
    w("## 1. 観点別 件数サマリ\n\n")
    w("| 観点 | 件数 | 内訳 |\n|---|---:|---|\n")
    for p in perspectives:
        rows_p = [r for r in target_rows if r["etype"] in p["etypes"]]
        bd = Counter(r["etype"] for r in rows_p)
        bd_str = " / ".join(f"{et}:{n}" for et, n in bd.most_common())
        w(f"| {p['name']} | {len(rows_p)} | {bd_str or '-'} |\n")
    w(f"| 大量操作バースト (参考) | {len(bursts)} ユーザ | per_min>={cfg['burst']['per_minute']} or per_5min>={cfg['burst']['per_5min']} |\n")
    w(f"| 国外IPからのログイン | {len(foreign_logins)} | - |\n")
    w(f"| 夜間帯(JST22-06)のリスク操作 | {len(night_rows)} | - |\n\n")

    # §2 管理者確認事項
    w("## 2. 管理者が確認すべき事項\n\n")
    for r in critical_rows:
        w(f"- **{fmt_ts(r['ts'])} / {r['user']}** — `{r['etype']}` : {short(r['edesc'],80)} → 実行目的・接続先・付与スコープを確認\n")
    for p in perspectives:
        rows_p = [r for r in target_rows if r["etype"] in p["etypes"]]
        if not rows_p:
            continue
        by_u = Counter(r["email"] or r["user"] for r in rows_p)
        top = ", ".join(f"{u}({n})" for u, n in by_u.most_common(3))
        w(f"- **{p['name']} {len(rows_p)} 件** — 実行者上位: {top}\n")
    if foreign_logins:
        w(f"- **国外IPからのログイン {len(foreign_logins)} 件** — 出張/VPN等の正当事由か確認\n")
    if night_rows:
        w(f"- **夜間帯リスク操作 {len(night_rows)} 件** — 業務時間外操作の妥当性を確認\n")
    if bursts:
        w(f"- **大量操作バースト {len(bursts)} ユーザ** — 退職前の情報収集・不正クローリング等の可能性を確認\n")
    w("\n")

    # §3 観点別 要確認イベント
    w("## 3. 観点別 要確認イベント\n\n")
    for idx, p in enumerate(perspectives, 1):
        rows_p = sorted(
            [r for r in target_rows if r["etype"] in p["etypes"]],
            key=lambda x: x["ts"] or datetime.min.replace(tzinfo=JST),
            reverse=True,
        )
        w(f"### 3.{idx} {p['name']} ({len(rows_p)} 件)\n\n")
        if not rows_p:
            w("該当なし。\n\n")
            continue
        if len(rows_p) > 30:
            ug = Counter((r["email"] or r["user"], r["etype"]) for r in rows_p)
            w("**ユーザ × 種別 (上位):**\n\n| ユーザ | 種別 | 件数 |\n|---|---|---:|\n")
            for (u, et), n in ug.most_common(15):
                w(f"| {u} | {et} | {n} |\n")
            w("\n<details><summary>個別イベント (新しい順 上位30件)</summary>\n\n")
            render_compact(rows_p, w, max_n=30)
            w("</details>\n\n")
        else:
            render_compact(rows_p, w)

    # §4 バースト
    w("## 4. 大量操作 / バースト\n\n")
    w(f"### 4.1 `{cfg['burst']['etype']}` バースト (per_min>={cfg['burst']['per_minute']} or per_5min>={cfg['burst']['per_5min']})\n\n")
    if bursts:
        w("| ユーザ | 1分最大 | 5分最大 | 期間内総数 |\n|---|---:|---:|---:|\n")
        for b in bursts[:20]:
            w(f"| {b['user']} | {b['max_per_minute']} | {b['max_per_5min']} | {b['total']} |\n")
        w("\n")
    else:
        w("検出なし。\n\n")

    # §5 国外ログイン
    w("## 5. 国外IPからのログイン\n\n")
    render_compact(
        sorted(foreign_logins, key=lambda x: x["ts"] or datetime.min.replace(tzinfo=JST)),
        w,
    )

    # §6 夜間
    w("## 6. 夜間帯 (JST 22:00–06:00) のリスク操作\n\n")
    render_compact(
        sorted(night_rows, key=lambda x: x["ts"] or datetime.min.replace(tzinfo=JST), reverse=True),
        w,
    )

    # §7 除外種別一覧
    w("## 7. 除外したアクティビティ種別\n\n")
    w("以下は今回のサマリーから除外している種別 (通常運用 / システム自動処理 / 重要度低 と判断したもの)。\n\n")
    w("| アクティビティ種別 | 件数 |\n|---|---:|\n")
    for et, n in sorted(result["all_etype_count"].items(), key=lambda x: -x[1]):
        if et not in target_etypes_set:
            w(f"| {et} | {n:,} |\n")
    w("\n")

    return out.getvalue()


def to_jsonable(o: Any) -> Any:
    if isinstance(o, datetime):
        return o.strftime("%Y-%m-%d %H:%M:%S%z")
    if isinstance(o, dict):
        return {k: to_jsonable(v) for k, v in o.items()}
    if isinstance(o, list):
        return [to_jsonable(x) for x in o]
    return o


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--config", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    cfg = load_config(args.config)
    result = analyze(args.csv_path, cfg)

    os.makedirs(args.out_dir, exist_ok=True)
    md_path = os.path.join(args.out_dir, "audit-summary.md")
    json_path = os.path.join(args.out_dir, "audit-summary.json")

    with open(md_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(render_markdown(result, cfg))
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(to_jsonable(result), f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "markdown": md_path,
        "json": json_path,
        "total_rows": result["total_rows"],
        "target_rows": len(result["target_rows"]),
        "critical_rows": len(result["critical_rows"]),
        "bursts": len(result["bursts"]),
        "foreign_logins": len(result["foreign_logins"]),
        "night_rows": len(result["night_rows"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
