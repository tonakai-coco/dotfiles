# Fish: wtn 初期化を追加

## Context

対話シェル起動時に `wtn` が入っていれば fish 用の初期化を読み込みたい。

## 対象環境

- **設定場所**: `config/fish/config.fish`
- **対応OS**: macOS（fish 設定）
- **条件**: `command -q wtn` が真のときのみ

## 実装内容

`status is-interactive` ブロック内で、zoxide と同様に:

```fish
if command -q wtn
    wtn init fish | source
end
```

未インストール環境では何もしない（idempotent）。

## 検証

- `fish -n config/fish/config.fish`
- `fish_indent` で対話ブロックのインデントを揃えた
