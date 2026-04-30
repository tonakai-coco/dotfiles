# `analyze_audit_log.py` の設定 JSON スキーマ

```json
{
  "perspectives": [
    {
      "name": "観点ラベル (Markdown 表に表示される)",
      "etypes": ["完全一致するアクティビティ種別名", "..."]
    }
  ],
  "critical_etypes": ["即座に §0 と §2 で重大として報告する種別"],
  "system_actors": ["件名がこれに一致するアクターは閲覧バースト集計から除外", "Notion App", "Notion AI", "Automation", "Notion Calendar"],
  "night_etypes": ["JST 22:00-06:00 に発生したら §6 夜間として別枠報告する種別"],
  "burst": {
    "etype": "バースト検出対象の種別 (典型的に 'ページを閲覧')",
    "per_minute": 100,
    "per_5min": 300
  },
  "domestic_country_codes": ["国外ログイン判定で 'これ以外なら国外' とする国コード", "JP"],
  "login_etype": "国外ログイン判定で対象とする種別 (デフォルト 'ログイン')"
}
```

## フィールド詳細

### `perspectives` (必須)
観点リスト。各要素は `{name, etypes}`。`etypes` は Notion CSV の「アクティビティ種別」列と **完全一致** で判定。部分一致はしない (誤検知防止)。

### `critical_etypes`
件数によらず最優先で報告したい種別。典型例: `外部/パブリックインテグレーションを接続`、SAML 無効化、MFA 解除など。

### `system_actors`
Notion 内部で動く自動処理。これらは `burst.etype` の集計から除外される。デフォルト: `Notion App`, `Notion AI`, `Automation`, `Notion Calendar`。

### `night_etypes`
夜間 (JST 22-06) に発生した場合に §6 で別枠報告する種別。**観点 etypes に含まれていなくても** 別途レポート対象になる。ただし `system_actors` 実行のものは除外される。

### `burst`
- `etype`: バースト検出対象の種別。通常は `ページを閲覧`。
- `per_minute`: 1 分あたりこの件数以上で検出。
- `per_5min`: 5 分あたりこの件数以上で検出。

どちらか一方を超えたら検出。

### `domestic_country_codes`
国コードの集合。`login_etype` に該当する行のうち、`国` 列がここに含まれず、かつ `不明` / 空 / `N/A` でもないものを「国外ログイン」として §5 で報告。

### `login_etype`
国外ログイン判定の対象種別。日本語ロケールでは通常 `ログイン`。

## 出力

スクリプトは `--out-dir` に以下を生成:

- `audit-summary.md` — 人間可読の Markdown レポート (固定章立て §0〜§7)
- `audit-summary.json` — 上記の生データ (target_rows, bursts, foreign_logins, night_rows, all_etype_count, period_jst 等)
