# LINE Bot Lambda Function

LINEからのWebhookを受信し、AgentCore Runtimeのエージェントと会話するLambda Function

## 機能

- LINE Webhookの受信と署名検証
- DynamoDBによるセッション管理（24時間TTL）
- AgentCore Runtimeの呼び出し
- LINE Reply APIでの応答

## テスト

### ユニットテスト

```bash
uv run pytest tests/test_lambda_function.py -v
```

### 統合テスト

デプロイ後に実行：

```bash
# LINE_CHANNEL_SECRETを設定
export LINE_CHANNEL_SECRET="your_channel_secret"

# 統合テストを実行
uv run pytest tests/test_integration.py -v -s
```

統合テストの内容：
- Lambda Function URLの存在確認
- 署名検証（正常/異常系）
- テキストメッセージの処理
- 日本語メッセージの処理
- セッション維持の確認
- DynamoDBへのセッション保存確認

## デプロイ

CDKスタックからデプロイされます：

```bash
cd ../cdk-agentcore
uv run cdk deploy
```

デプロイ後、以下の環境変数を手動で設定：
- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_CHANNEL_SECRET`

## 環境変数

| 変数名 | 説明 | 必須 |
|--------|------|------|
| LINE_CHANNEL_ACCESS_TOKEN | LINE Messaging APIのアクセストークン | ✓ |
| LINE_CHANNEL_SECRET | LINE Messaging APIのチャネルシークレット | ✓ |
| AGENT_RUNTIME_ARN | AgentCore RuntimeのARN | ✓ |
| SESSION_TABLE_NAME | DynamoDBテーブル名 | ✓ |
| AWS_DEFAULT_REGION | AWSリージョン（自動設定） | - |

## アーキテクチャ

```
LINE User → LINE Platform → Lambda Function URL → Lambda Function
                                                        ↓
                                                   DynamoDB (Session)
                                                        ↓
                                                   AgentCore Runtime
                                                        ↓
                                                   LINE Reply API
```

## セッション管理

- LINE User ID → AgentCore Session IDのマッピング
- 初回メッセージ時に新規セッション作成
- 24時間TTLで自動削除
- メッセージ受信時にTTLを更新
