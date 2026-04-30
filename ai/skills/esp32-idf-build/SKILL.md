---
name: esp32-idf-build
description: >
  Windows 環境で ESP-IDF を使って ESP32 プロジェクトをビルド・フラッシュ・モニターする手順。
  ユーザーが「ESP32 をビルドして」「idf.py でビルドしたい」「ESP32 に書き込みたい」
  「フラッシュしてモニターしたい」「ESP-IDF のビルドが通らない」など、
  ESP-IDF を使った開発作業に言及したら必ずこのスキルを使うこと。
  menuconfig での設定変更が必要な場面にも対応する。
---

# ESP32 ESP-IDF ビルド・フラッシュ・モニター（Windows）

## 重要：環境セットアップ（毎回必須）

**idf.py を実行する前に、必ず以下のスクリプトを source すること。**
これを忘れると `idf.py` が見つからないか、誤った環境で実行されてしまう。

```powershell
. C:\Espressif\tools\Microsoft.v6.0.PowerShell_profile.ps1
```

このスクリプトが行うこと：
- `IDF_PATH`、`IDF_TOOLS_PATH` などの環境変数を設定
- Python 仮想環境をアクティブ化
- `idf.py`、`esptool.py` などのコマンドを使えるようにする

## 基本ワークフロー

### 1. ビルドのみ

```powershell
. C:\Espressif\tools\Microsoft.v6.0.PowerShell_profile.ps1
Set-Location <プロジェクトディレクトリ>
idf.py build
```

### 2. ビルド → フラッシュ → モニター（最もよく使うパターン）

```powershell
. C:\Espressif\tools\Microsoft.v6.0.PowerShell_profile.ps1
Set-Location <プロジェクトディレクトリ>
idf.py -p <COMポート> flash monitor
```

- `<COMポート>` 例: `COM3`、`COM4` など（デバイスマネージャーで確認）
- モニターを終了するには `Ctrl-]`

### 3. フラッシュのみ（ビルド済みの場合）

```powershell
idf.py -p <COMポート> flash
```

### 4. モニターのみ（フラッシュ済みの場合）

```powershell
idf.py -p <COMポート> monitor
```

## プロジェクト設定変更（menuconfig）

Wi-Fi 認証情報、MQTT ブローカー URI などをプロジェクトに焼き込む場合は menuconfig を使う。

```powershell
. C:\Espressif\tools\Microsoft.v6.0.PowerShell_profile.ps1
Set-Location <プロジェクトディレクトリ>
idf.py menuconfig
```

設定値は `sdkconfig` ファイルに保存される（`.gitignore` 対象にすること）。

## コマンドを1行で連結する場合

PowerShell のセミコロン区切りで繋げると source し直す手間が省ける：

```powershell
. C:\Espressif\tools\Microsoft.v6.0.PowerShell_profile.ps1; Set-Location <プロジェクトディレクトリ>; idf.py build
```

## 環境情報（このセットアップ固有）

| 項目 | 値 |
|------|-----|
| IDF バージョン | v6.0 |
| IDF_PATH | `C:\esp\v6.0\esp-idf` |
| IDF_TOOLS_PATH | `C:\Espressif\tools` |
| PS プロファイル | `C:\Espressif\tools\Microsoft.v6.0.PowerShell_profile.ps1` |

## よくあるトラブル

### `idf.py` が見つからない
→ PowerShell プロファイルを source し忘れている。必ず先頭行に `. C:\Espressif\tools\Microsoft.v6.0.PowerShell_profile.ps1` を実行する。

### シリアルポートが開けない（フラッシュ失敗）
→ ESP32 が PC に接続されているか確認。COM ポート番号はデバイスマネージャーの「ポート (COM と LPT)」で確認する。

### ビルドエラー（コンポーネントが見つからない）
→ `dependencies.lock` が最新か確認。`idf.py update-dependencies` を実行してみる。

### sdkconfig が古い状態になっている
→ `idf.py fullclean` でビルドキャッシュをクリアしてからビルドし直す。
