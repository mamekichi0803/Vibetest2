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
| Teatro alla Scala | `scala` | 実装済み・実サイトで1126件取得を確認（2026-07-08）。カレンダーグリッドの前後月パディング日と思われる無効な日付（例:「31 April」）は警告を出してスキップ |
| Wiener Staatsoper | `wiener_staatsoper` | 実装済み・実行ログを元に修正し実サイトで動作確認済み（2026-07-08）。当初はスクリーンショットから日付を「日」「月」別行と誤認しており0件だったが、実際は「04 Sep」のように1行だった |
| Royal Ballet and Opera | `rbo` | 実装済み・実行ログを元に完全書き換えし動作確認済み（2026-07-08）。デフォルト表示はスクリーンショットで見た日毎カレンダー（要「Expand all」）ではなく、日付範囲付きのカード一覧（List view）だった |
| Opéra national de Paris | `paris_opera` | 実装済み・実サイトで7件取得を確認（2026-07-08）。カード形式で個別公演日ではなく上演期間（開始日〜終了日）を取得 |
| Metropolitan Opera | `met_opera` | 実装済み・実行ログを元に完全書き換えし動作確認済み（2026-07-08）。当初は日別アジェンダ（詳細ポップアップ）を想定していたが、実際のデフォルト表示は「EVENTS FOR <MONTH>」+日付番号のグリッド形式だった。月切り替え（日付ピッカー操作）は未対応で現在表示中の月のみ取得 |

5館とも実装済みで、2026-07-08 の GitHub Actions 実行ログ（`-v`）を元に実際のページ構造を確認・修正済みです。
とはいえ全パターン（Scala の過去/将来レンジ、Met の月切り替えなど）を検証しきれてはいません。
パーサーが実際の構造とズレた場合は空リストを返すだけで実行自体は失敗しませんが、
`No performances extracted for ...` という警告がログに出ます（実際に取得した生テキストも
ログに含まれるので、それを元に調整できます）。

### 実サイトのHTML/描画結果を確認する方法について

この開発環境（サンドボックス）はセキュリティポリシーにより、上記オペラハウスのドメインへの
アウトバウンド通信がネットワークレベルで完全にブロックされています（`curl` / `WebFetch` /
Headless Chromium（Playwright）のいずれでも同じ結果）。そのため、各サイトの実際のHTML構造を
この環境から直接確認することができません。

パーサーの動作がおかしい場合や、新しいサイトを追加する場合は、以下のいずれかの方法で実データを共有してください。

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
- 5館のパーサー（`scala` / `wiener_staatsoper` / `rbo` / `paris_opera` / `met_opera`）はいずれも
  スクリーンショット数枚から推測した表示テキストのパターンに基づいており、実サイトでの動作は
  未検証です。初回実行時にログ（`-v` オプション）を確認し、`No performances extracted for ...`
  という警告が出た場合は調整が必要です。
- Bot対策（Cloudflare等）が強いサイトでは Headless Chromium でもブロックされる可能性があります。
  その場合は User-Agent/待機時間の調整や、別のアプローチ（公式APIの利用など）が必要です。
- Met Opera は月切り替えが日付ピッカーのUI操作を要するため、現状は初回表示時点の月のみ取得します。
  複数月分が必要になった場合は要拡張です（`opera_schedule_tracker/sources/met_opera.py` 参照）。
- Opéra national de Paris のみ、個別公演の日時ではなく「上演期間（開始日〜終了日）」を返します
  （ページ自体が公演ごとの個別日程を一覧に表示していないため）。

## テスト

```bash
pip install -r requirements-dev.txt
pytest
```
