# LINE Bot with AgentCore Runtime Architecture

## Overview

LINEからBedrock AgentCore Runtimeのエージェントと会話できるシステムのアーキテクチャ

## Architecture Diagram

```
LINE User
    ↓ (メッセージ送信)
LINE Platform
    ↓ (Webhook POST)
Lambda Function URL
    ↓
Lambda Function (Webhook Handler)
    ↓ (invoke-agent-runtime)
Bedrock AgentCore Runtime
    ↓ (応答)
Lambda Function
    ↓ (Reply API)
LINE Platform
    ↓
LINE User (応答受信)
```

## Components

### 1. LINE Messaging API
- **Webhook**: ユーザーからのメッセージを受信
- **Reply API**: ユーザーにメッセージを返信
- **認証**: Channel Access Token & Channel Secret

### 2. Lambda Function (Webhook Handler)
- **言語**: Node.js/TypeScript
- **フレームワーク**: Hono (軽量Webフレームワーク)
- **機能**:
  - LINE Webhookの受信
  - 署名検証（セキュリティ）
  - AgentCore Runtimeの呼び出し
  - LINE Reply APIでの応答

### 3. Bedrock AgentCore Runtime
- **エージェント**: Strandsベースのエージェント
- **モデル**: Claude 3.5 Sonnet v2
- **セッション管理**: ユーザーごとの会話履歴を保持

### 4. DynamoDB (セッション管理)
- **用途**: LINE User ID → AgentCore Session IDのマッピング
- **TTL**: 24時間（会話セッションの有効期限）

## Data Flow

1. ユーザーがLINEでメッセージを送信
2. LINE PlatformがWebhook URLにPOSTリクエスト
3. Lambda Functionが署名を検証
4. DynamoDBからセッションIDを取得（なければ新規作成）
5. AgentCore Runtimeを呼び出し（セッションID付き）
6. エージェントの応答を受信
7. LINE Reply APIで応答を返信

## Session Management Strategy

- **セッションキー**: LINE User ID
- **セッション作成**: 初回メッセージ時
- **セッション維持**: 24時間
- **セッション更新**: メッセージ受信時にTTLを更新

## Security

- LINE署名検証（X-Line-Signature）
- Lambda Function URLは認証なし（LINE署名で保護）
- 環境変数でシークレット管理
- IAM Roleで最小権限の原則

## Environment Variables

- `LINE_CHANNEL_ACCESS_TOKEN`: LINE Messaging APIのアクセストークン
- `LINE_CHANNEL_SECRET`: LINE Messaging APIのチャネルシークレット
- `AGENT_RUNTIME_ARN`: AgentCore RuntimeのARN
- `SESSION_TABLE_NAME`: DynamoDBテーブル名
- `AWS_REGION`: AWSリージョン（デフォルト: us-west-2）

## Cost Considerations

- Lambda: 実行時間とメモリ使用量に応じた課金
- AgentCore Runtime: セッション時間とリクエスト数に応じた課金
- DynamoDB: オンデマンドモード（読み書き回数に応じた課金）
- データ転送: 無視できるレベル

## Scalability

- Lambda: 自動スケーリング（同時実行数制限あり）
- AgentCore Runtime: AWSが自動スケーリング
- DynamoDB: オンデマンドモードで自動スケーリング

## Monitoring & Logging

- CloudWatch Logs: Lambda実行ログ
- CloudWatch Metrics: Lambda実行回数、エラー率
- X-Ray: 分散トレーシング（オプション）

## Future Enhancements

- リッチメニュー対応
- Flex Message対応
- 画像・位置情報などのメディア対応
- グループチャット対応
- プッシュメッセージ機能
- 会話履歴の分析・可視化

## References

- [LINE Messaging API](https://developers.line.biz/en/reference/messaging-api/)
- [AWS Bedrock AgentCore](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
- [Hono Framework](https://hono.dev/)
