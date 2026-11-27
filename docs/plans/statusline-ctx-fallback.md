# Windows のステータスラインで ctx 表示が消えないようにする

## 背景

Claude Code とのやり取りの途中で、ステータスラインの ctx（コンテキスト使用率）表示が消えることがある。
`context_window.used_percentage` はコンパクト直後や応答待ちの間などに null になり、旧スクリプトは null のとき ctx 表示を省略していた。

## 対象 OS・ディレクトリ

- Windows
- `ai/claude/windows/statusline-command.ps1`

## 変更内容

- `used_percentage` が null のときは `total_input_tokens / context_window_size` から使用率を計算する
- それも取れないときは、`$env:TEMP\claude-statusline-ctx-<session_id>.txt` に保存した直前の値を `~` 付きで表示する（`~` は最新値でない印）
- 使用率が取れたときはキャッシュファイルを更新する
- キャッシュファイル名に使う `session_id` は英数字とハイフンだけ残す。空になったらキャッシュを使わない（レビュー指摘への対応）
- フォールバック計算ではトークン数 0 も有効値として扱い `ctx 0%` を表示する。`context_window_size` が 0 以下のときは計算しない（レビュー指摘への対応）

## 対象外

- macOS / Linux のステータスライン
- リンク定義と `Makefile`（変更なし）

## 検証

- サンプル JSON を標準入力に渡してスクリプトを実行し、次を確認した
  - `used_percentage: 42` → `ctx 42%`
  - 同じ session で `used_percentage: null` → `~ctx 42%`
  - `used_percentage: null` で `total_input_tokens: 50000` / `context_window_size: 200000` → `ctx 25%`
  - `context_window` なし・キャッシュなし → ctx 表示なし、エラーなし
  - `session_id: "../../evil:x"` → `$env:TEMP\claude-statusline-ctx-evilx.txt` にだけ書き込まれる
  - `session_id` が空または無い → キャッシュを読み書きしない
  - キャッシュ `ctx 42%` がある状態で `total_input_tokens: 0` → `ctx 0%`
  - `context_window_size: 0` → 計算せずキャッシュの値を `~` 付きで表示
- 実際のセッションでの表示消失の再現は未実施
- リンク定義の変更がないため `make check` / `make status` は未実施
