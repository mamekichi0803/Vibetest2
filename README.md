# Vibetest2 — Opera Schedule Tracker

世界の主要オペラハウスの公演スケジュール（新規追加・変更・削除）を定期的にチェックし、
差分があればメールで通知するプログラムです。

## 仕組み

1. `config/opera_houses.yaml` に登録された各オペラハウスの公演ページを取得します。
   `parser` フィールドで、そのサイト用の取得・解析関数
   （`opera_schedule_tracker/sources/PARSERS` に登録）を指定します。
   - `jsonld`: ページに埋め込まれた schema.org `Event` 構造化データ（JSON-LD）を解析する汎用パーサー
     （`sources/generic_jsonld.py`）。HTML構造に依存しないため対応サイトには最も頑丈です。
   - JSON-LD を持たないサイトはサイト専用パーサー（例: `sources/scala.py`）を使います。
     JavaScriptで描画されるページ（例: Met Opera）は `opera_schedule_tracker/browser.py` の
     Headless Chromium（Playwright）でレンダリングしてからテキストを解析します。
2. 前回実行時の結果（`data/state.json`）と比較し、新規追加・削除・変更された公演を検出します
   （`opera_schedule_tracker/state.py`）。
3. 差分があれば SMTP 経由でメールを送信します（`opera_schedule_tracker/notifier.py`）。
   送信先はデフォルトで `shinmotoi2000@gmail.com` です。
4. GitHub Actions（`.github/workflows/opera-schedule-tracker.yml`）が毎日定時に実行し、
   最新の `data/state.json` をリポジトリにコミットします。

## 対象オペラハウスと実装状況

| オペラハウス | parser | 状況 |
|---|---|---|
| Teatro alla Scala | `scala` | 実装済み（スクリーンショットを元に設計、ユニットテスト済み） |
| Wiener Staatsoper | `wiener_staatsoper` | 未実装（月別URL生成のみ実装済み。実データ待ち） |
| Royal Ballet and Opera | `rbo` | 未実装（実データ待ち） |
| Opéra national de Paris | `paris_opera` | 未実装（実データ待ち） |
| Metropolitan Opera | `met_opera` | 未実装（実データ待ち。JS描画のためAPIエンドポイント調査が理想） |

**未実装のパーサーは警告をログに出して空リストを返すだけ**なので、実行自体は失敗しません。
実データが手に入り次第、`opera_schedule_tracker/sources/scala.py` と同じパターンで実装します。

### 実サイトのHTML/描画結果を確認する方法について

この開発環境（サンドボックス）はセキュリティポリシーにより、上記オペラハウスのドメインへの
アウトバウンド通信がネットワークレベルで完全にブロックされています（`curl` / `WebFetch` /
Headless Chromium（Playwright）のいずれでも同じ結果）。そのため、各サイトの実際のHTML構造を
この環境から直接確認することができません。

未実装のサイトを実装する際は、以下のいずれかの方法で実データを共有してください。

1. （最も正確）ブラウザの検証ツール（DevTools）で該当箇所を右クリック →
   「Copy」→「Copy outerHTML」→ チャットに貼り付け
2. ページソース（`Ctrl+U` 等）をコピーして貼り付け
3. カレンダー/一覧画面のスクリーンショット（今回 La Scala で使った方法。class名までは分からないため
   表示テキストのパターンに基づく簡易パーサーになります）
4. Met Opera のようにJavaScriptで描画されるサイトは、可能であればブラウザDevToolsの
   「Network」タブ（Fetch/XHRでフィルタ）で、公演データを返しているAPIリクエストのURLと
   レスポンスJSONも共有してください。CSSセレクタより堅牢なパーサーが書けます。

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
Playwright（Headless Chromium）を使うため、ワークフロー内で `playwright install --with-deps chromium`
を実行してブラウザ本体をインストールしています。

### 3. ローカルでの実行

```bash
pip install -r requirements.txt
playwright install --with-deps chromium

# 送信・保存を行わず、差分だけ確認したい場合
python -m opera_schedule_tracker.main --dry-run -v

# 実際にメール送信・状態保存を行う場合（環境変数の設定が必要）
export SMTP_USER=your-account@gmail.com
export SMTP_PASSWORD=xxxxxxxxxxxxxxxx
python -m opera_schedule_tracker.main -v
```

`SMTP_USER` / `SMTP_PASSWORD` が未設定の場合、メールは送信されず差分がログに出力されるだけです。

## オペラハウスの追加・調整

`config/opera_houses.yaml` に `name` / `url` / `parser` を追記し、対応する `parser` を
`opera_schedule_tracker/sources/` に実装（`sources/__init__.py` の `PARSERS` に登録）してください。
JSON-LD が使えるサイトなら `parser: jsonld` を指定するだけで対応できます。

## 制限事項・注意点

- 各オペラハウスの公式サイトはシーズンごとに URL やページ構造が変わることがあります。
  取得件数が急に 0 件になった場合は、`config/opera_houses.yaml` の URL やサイト構造を確認してください。
- `scala` パーサーはスクリーンショット1枚から推測した表示テキストのパターンに基づいており、
  実サイトでの動作は未検証です。初回実行時にログ（`-v` オプション）を確認し、
  `No performances extracted for ...` という警告が出た場合は調整が必要です。
- Bot対策（Cloudflare等）が強いサイトでは Headless Chromium でもブロックされる可能性があります。
  その場合は User-Agent/待機時間の調整や、別のアプローチ（公式APIの利用など）が必要です。

## テスト

```bash
pip install -r requirements-dev.txt
pytest
```
