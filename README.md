# Vibetest2 — Opera Schedule Tracker

世界の主要オペラハウスの公演スケジュール（新規追加・変更・削除）を定期的にチェックし、
差分があればメールで通知するプログラムです。

## 仕組み

1. `config/opera_houses.yaml` に登録された各オペラハウスの "What's on" ページを取得します。
2. ページに埋め込まれた schema.org の `Event` 構造化データ（JSON-LD）を解析し、
   公演タイトル・日時・会場・URL を抽出します（`opera_schedule_tracker/sources/generic_jsonld.py`）。
   個別サイトの見た目（CSS/HTML構造）に依存しないため、デザイン変更に強い方式です。
3. 前回実行時の結果（`data/state.json`）と比較し、新規追加・削除・変更された公演を検出します
   （`opera_schedule_tracker/state.py`）。
4. 差分があれば SMTP 経由でメールを送信します（`opera_schedule_tracker/notifier.py`）。
   送信先はデフォルトで `shinmotoi2000@gmail.com` です。
5. GitHub Actions（`.github/workflows/opera-schedule-tracker.yml`）が毎日定時に実行し、
   最新の `data/state.json` をリポジトリにコミットします。

対象のオペラハウス（`config/opera_houses.yaml` で追加・変更可能）:

- Metropolitan Opera（ニューヨーク）
- Royal Opera House（ロンドン）
- Wiener Staatsoper（ウィーン）
- Teatro alla Scala（ミラノ）
- Opéra national de Paris（パリ）
- Bayerische Staatsoper（ミュンヘン）
- Semperoper Dresden（ドレスデン）
- Deutsche Oper Berlin（ベルリン）

## セットアップ

### 1. メール送信用の認証情報（GitHub Secrets）

`shinmotoi2000@gmail.com` へ送信するには、Gmail の「アプリパスワード」を発行し、
リポジトリの Settings > Secrets and variables > Actions に以下を登録してください。

| Secret name       | 説明                                             | 例                        |
|--------------------|--------------------------------------------------|---------------------------|
| `SMTP_USER`         | 送信元 Gmail アドレス                            | `your-account@gmail.com`  |
| `SMTP_PASSWORD`     | Gmail アプリパスワード（16桁）                    | `abcd efgh ijkl mnop`      |
| `SMTP_HOST`         | 省略可。デフォルト `smtp.gmail.com`               | `smtp.gmail.com`           |
| `SMTP_PORT`         | 省略可。デフォルト `465`（SSL）                   | `465`                      |
| `RECIPIENT_EMAIL`   | 省略可。デフォルト `shinmotoi2000@gmail.com`      | `shinmotoi2000@gmail.com`  |

Gmail 以外の SMTP サーバーを使う場合も、上記の環境変数で切り替えられます
（`SMTP_USE_SSL=false` にすると STARTTLS を使用）。

### 2. 実行スケジュール

`.github/workflows/opera-schedule-tracker.yml` は毎日 09:00 JST (00:00 UTC) に実行されます。
`workflow_dispatch` も有効なので、GitHub の Actions タブから手動実行して即座に試すこともできます。

### 3. ローカルでの実行

```bash
pip install -r requirements.txt

# 送信・保存を行わず、差分だけ確認したい場合
python -m opera_schedule_tracker.main --dry-run -v

# 実際にメール送信・状態保存を行う場合（環境変数の設定が必要）
export SMTP_USER=your-account@gmail.com
export SMTP_PASSWORD=xxxxxxxxxxxxxxxx
python -m opera_schedule_tracker.main -v
```

`SMTP_USER` / `SMTP_PASSWORD` が未設定の場合、メールは送信されず差分がログに出力されるだけです。

## オペラハウスの追加・調整

`config/opera_houses.yaml` に `name` と `url` を追記するだけで対象を追加できます。
対象ページが JSON-LD の `Event` 構造化データを含んでいない場合は自動抽出できないため、
その場合は `opera_schedule_tracker/sources/` に専用パーサーを追加してください。

## 制限事項・注意点

- 各オペラハウスの公式サイトはシーズンごとに URL やページ構造が変わることがあります。
  取得件数が急に 0 件になった場合は、`config/opera_houses.yaml` の URL やサイト構造を確認してください。
- 本リポジトリの開発環境（サンドボックス）は外部サイトへのネットワークアクセスが制限されているため、
  各オペラハウスの実サイトに対する動作確認は行っていません。初回実行時にログ（`-v` オプション）を
  確認し、`No JSON-LD Event data found for ...` という警告が出た場合は該当サイトの構造を調整してください。

## テスト

```bash
pip install -r requirements-dev.txt
pytest
```
