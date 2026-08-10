## Purpose

Supabase無料プランのDBをアクティブに保つための定期的なkeep-alive機能を提供する。スケジュールされたHTTPリクエストによりDBコネクションを維持し、プロジェクトの一時停止を防ぐ。

## ADDED Requirements

### Requirement: Keep-alive endpoint
バックエンドはDBにpingを発行する認証不要のエンドポイントを提供しなければならない（MUST）。

#### Scenario: Successful DB ping
- **WHEN** クライアントが `/keepalive` エンドポイントにGETリクエストを送信する
- **THEN** システムはDBに `SELECT 1` を発行し、成功時にHTTP 200とステータスJSONを返す

#### Scenario: DB connection failure
- **WHEN** DB接続に失敗する
- **THEN** システムはHTTP 503とエラー情報を含むJSONを返す

### Requirement: Scheduled keep-alive execution
GitHub Actionsのcronスケジュールにより定期的にkeep-aliveリクエストが自動実行されなければならない（MUST）。

#### Scenario: Scheduled ping execution
- **WHEN** cronスケジュールがトリガーされる（3日ごと）
- **THEN** ワークフローは本番環境のkeep-aliveエンドポイントにHTTPリクエストを送信する

#### Scenario: Ping failure notification
- **WHEN** keep-aliveリクエストが非2xxステータスを返す
- **THEN** ワークフローは失敗ステータスで終了し、GitHub Actionsの通知が発生する

### Requirement: Configurable target URL
keep-aliveターゲットURLはGitHub Actions変数で設定可能でなければならない（MUST）。

#### Scenario: Custom URL configuration
- **WHEN** `KEEPALIVE_URL` GitHub変数が設定されている
- **THEN** ワークフローはその変数の値をターゲットURLとして使用する

#### Scenario: Default URL fallback
- **WHEN** `KEEPALIVE_URL` が設定されていない
- **THEN** ワークフローはデフォルトの本番URL（`https://mjai-nine.vercel.app/api/keepalive`）を使用する
