# テスト・デバッグ・トラブルシューティングガイド

## 目次

1. [テスト方法](#テスト方法)
2. [AWSリソースの確認](#awsリソースの確認)
3. [ログの確認](#ログの確認)
4. [トラブルシューティング](#トラブルシューティング)
5. [パフォーマンス監視](#パフォーマンス監視)

---

## テスト方法

### 1. ユニットテスト（CDK）

CDKスタックの構成をテスト：

```bash
cd cdk-agentcore
uv run pytest tests/unit/test_cdk_agentcore_stack.py -v
```

**テスト内容:**
- AgentCore Runtimeの作成確認
- IAM Roleの設定確認
- DynamoDBテーブルの作成確認
- Lambda Functionの設定確認
- 出力値の存在確認

### 2. 統合テスト（Lambda Function）

デプロイ済みのLambda Functionをテスト：

```bash
cd line-bot-lambda

# 環境変数を設定（direnvを使用）
direnv allow

# 統合テストを実行
uv run pytest tests/test_integration.py -v -s
```

**テスト内容:**
- Webhook URLの存在確認
- 署名検証（正常/異常系）
- メッセージ処理
- セッション管理
- DynamoDBへのデータ保存

### 3. AgentCore Runtimeのテスト

エージェント単体のテスト：

```bash
cd cdk-agentcore
uv run pytest tests/integration/test_deployed_agent.py -v -s
```

**テスト内容:**
- 基本的な応答
- 日本語対応
- 計算処理
- 複数リクエストの処理

### 4. 手動テスト（LINE Bot）

1. **LINEアプリでBotを友だち追加**
2. **メッセージを送信:**
   ```
   こんにちは！
   ```
3. **応答を確認**
4. **会話の継続性をテスト:**
   ```
   What is 10 + 5?
   What was my previous question?
   ```

---

## AWSリソースの確認

### CloudFormationスタック

スタックの状態を確認：

```bash
# スタック情報を表示
aws cloudformation describe-stacks \
  --stack-name CdkAgentcoreStack \
  --region us-west-2 \
  --query 'Stacks[0].[StackStatus,CreationTime,LastUpdatedTime]' \
  --output table

# スタックの出力値を表示
aws cloudformation describe-stacks \
  --stack-name CdkAgentcoreStack \
  --region us-west-2 \
  --query 'Stacks[0].Outputs' \
  --output table
```

### Lambda Function

#### 関数の基本情報

```bash
# Lambda関数の一覧
aws lambda list-functions \
  --region us-west-2 \
  --query "Functions[?starts_with(FunctionName, 'CdkAgentcoreStack')].{Name:FunctionName,Runtime:Runtime,Memory:MemorySize,Timeout:Timeout}" \
  --output table

# 特定の関数の詳細
FUNCTION_NAME=$(aws lambda list-functions \
  --region us-west-2 \
  --query "Functions[?starts_with(FunctionName, 'CdkAgentcoreStack-LineBotWebhookHandler')].FunctionName" \
  --output text)

aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region us-west-2 \
  --output json | jq
```

#### 環境変数の確認

```bash
# 環境変数を表示（トークンはマスクされる）
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region us-west-2 \
  --query 'Environment.Variables' \
  --output json | jq
```

#### Lambda Function URLの確認

```bash
# Function URLを取得
aws lambda get-function-url-config \
  --function-name "$FUNCTION_NAME" \
  --region us-west-2 \
  --query 'FunctionUrl' \
  --output text
```

### DynamoDB

#### テーブル情報

```bash
# テーブルの詳細
aws dynamodb describe-table \
  --table-name LineAgentSessions \
  --region us-west-2 \
  --query 'Table.{Name:TableName,Status:TableStatus,ItemCount:ItemCount,Size:TableSizeBytes}' \
  --output table

# TTL設定の確認
aws dynamodb describe-time-to-live \
  --table-name LineAgentSessions \
  --region us-west-2 \
  --output json | jq
```

#### セッションデータの確認

```bash
# 全セッションを表示
aws dynamodb scan \
  --table-name LineAgentSessions \
  --region us-west-2 \
  --output json | jq

# 特定ユーザーのセッションを取得
aws dynamodb get-item \
  --table-name LineAgentSessions \
  --key '{"user_id": {"S": "USER_ID_HERE"}}' \
  --region us-west-2 \
  --output json | jq
```

### AgentCore Runtime

#### Runtime情報

```bash
# Runtime IDを取得
RUNTIME_ID=$(aws cloudformation describe-stacks \
  --stack-name CdkAgentcoreStack \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentRuntimeId`].OutputValue' \
  --output text)

echo "Runtime ID: $RUNTIME_ID"

# Runtime ARNを取得
RUNTIME_ARN=$(aws cloudformation describe-stacks \
  --stack-name CdkAgentcoreStack \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentRuntimeArn`].OutputValue' \
  --output text)

echo "Runtime ARN: $RUNTIME_ARN"
```

#### Runtimeのテスト

```bash
# エージェントを直接呼び出し
python3 << 'EOF'
import boto3
import json

client = boto3.client("bedrock-agentcore", region_name="us-west-2")

payload = {"prompt": "Hello! How are you?"}
runtime_arn = "arn:aws:bedrock-agentcore:us-west-2:889119567707:runtime/my_agent-TWUz4HCBfP"

response = client.invoke_agent_runtime(
    agentRuntimeArn=runtime_arn,
    payload=json.dumps(payload).encode("utf-8")
)

result = json.loads(response["response"].read())
print(json.dumps(result, indent=2, ensure_ascii=False))
EOF
```

### AgentCore Memory

#### メモリリソースの確認

```bash
# メモリリソース一覧
aws bedrock-agentcore-control list-memories \
  --region us-west-2 \
  --output json | jq '.memories[] | {id: .id, name: .name, status: .status}'

# メモリの詳細（戦略・設定を含む）
MEMORY_ID="<memory-id>"

aws bedrock-agentcore-control get-memory \
  --memory-id "$MEMORY_ID" \
  --region us-west-2 \
  --output json | jq '.memory | {name: .name, status: .status, eventExpiryDuration: .eventExpiryDuration, strategies: [.strategies[] | {name: .name, type: .type, namespaces: .namespaces, status: .status}]}'
```

#### 短期記憶（Events）の確認

```bash
# セッション内の会話履歴を確認
# actorId: groupId（グループ）またはuserId（個人）
# sessionId: DynamoDBに保存されているsession_id
MEMORY_ID="<memory-id>"
ACTOR_ID="<groupId or userId>"
SESSION_ID="<session-id>"

aws bedrock-agentcore list-events \
  --memory-id "$MEMORY_ID" \
  --actor-id "$ACTOR_ID" \
  --session-id "$SESSION_ID" \
  --region us-west-2 \
  --output json | jq '.events[] | {eventId: .eventId, timestamp: .eventTimestamp}'
```

#### 長期記憶（Memory Records）の確認

```bash
# 戦略ごとの長期記憶レコードを確認
MEMORY_ID="<memory-id>"
STRATEGY_ID="<strategy-id>"   # get-memory で確認できる
ACTOR_ID="<groupId or userId>"

# SEMANTIC（家族の基本情報・事実）
aws bedrock-agentcore list-memory-records \
  --memory-id "$MEMORY_ID" \
  --namespace "/family/${ACTOR_ID}/facts" \
  --region us-west-2 \
  --output json | jq '.memoryRecordSummaries[] | {id: .memoryRecordId, content: .content.text}'

# USER_PREFERENCE（好み・設定）
aws bedrock-agentcore list-memory-records \
  --memory-id "$MEMORY_ID" \
  --namespace "/family/${ACTOR_ID}/preferences" \
  --region us-west-2 \
  --output json | jq '.memoryRecordSummaries[] | {id: .memoryRecordId, content: .content.text}'

# EPISODIC（出来事・イベント）
aws bedrock-agentcore list-memory-records \
  --memory-id "$MEMORY_ID" \
  --namespace "/family/${ACTOR_ID}/episodes" \
  --region us-west-2 \
  --output json | jq '.memoryRecordSummaries[] | {id: .memoryRecordId, content: .content.text}'

# キーワードでセマンティック検索
aws bedrock-agentcore retrieve-memory-records \
  --memory-id "$MEMORY_ID" \
  --namespace "/family/${ACTOR_ID}/facts" \
  --search-criteria '{"searchQuery": "アレルギー", "topK": 5}' \
  --region us-west-2 \
  --output json | jq '.memoryRecordSummaries[] | {score: .score, content: .content.text}'
```

#### メモリ抽出ジョブの確認

```bash
# 長期記憶への変換ジョブ状況（短期→長期の自動抽出）
aws bedrock-agentcore list-memory-extraction-jobs \
  --memory-id "$MEMORY_ID" \
  --region us-west-2 \
  --output json | jq '.jobs[] | {jobId: .jobID, status: .status, failureReason: .failureReason}'

# 失敗したジョブのみ確認
aws bedrock-agentcore list-memory-extraction-jobs \
  --memory-id "$MEMORY_ID" \
  --region us-west-2 \
  --output json | jq '[.jobs[] | select(.status == "FAILED")]'
```

---

## ログの確認

### CloudWatch Logs

#### Lambda Functionのログ

```bash
# ログストリームの一覧
aws logs describe-log-streams \
  --log-group-name "/aws/lambda/$FUNCTION_NAME" \
  --region us-west-2 \
  --order-by LastEventTime \
  --descending \
  --max-items 5 \
  --query 'logStreams[*].logStreamName' \
  --output table

# 最新のログをリアルタイムで表示
aws logs tail "/aws/lambda/$FUNCTION_NAME" \
  --follow \
  --region us-west-2

# 過去5分間のログを表示
aws logs tail "/aws/lambda/$FUNCTION_NAME" \
  --since 5m \
  --region us-west-2

# エラーログのみを表示
aws logs tail "/aws/lambda/$FUNCTION_NAME" \
  --since 1h \
  --region us-west-2 \
  --filter-pattern "ERROR"
```

#### AgentCore Runtimeのログ

```bash
# Runtime IDを使用してログを確認
LOG_GROUP="/aws/bedrock-agentcore/runtimes/${RUNTIME_ID}-DEFAULT"

# 最新のログを表示
aws logs tail "$LOG_GROUP" \
  --since 10m \
  --region us-west-2

# エラーログを検索
aws logs tail "$LOG_GROUP" \
  --since 1h \
  --region us-west-2 \
  --filter-pattern "ERROR"
```

### ログの分析

#### エラーパターンの検索

```bash
# Lambda関数のエラーを検索
aws logs filter-log-events \
  --log-group-name "/aws/lambda/$FUNCTION_NAME" \
  --region us-west-2 \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR" \
  --query 'events[*].message' \
  --output text

# 特定のエラーメッセージを検索
aws logs filter-log-events \
  --log-group-name "/aws/lambda/$FUNCTION_NAME" \
  --region us-west-2 \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --filter-pattern "AccessDeniedException" \
  --query 'events[*].message' \
  --output text
```

---

## トラブルシューティング

### 1. LINEからメッセージが届かない

#### 確認項目

```bash
# 1. Webhook URLが正しく設定されているか
aws lambda get-function-url-config \
  --function-name "$FUNCTION_NAME" \
  --region us-west-2

# 2. Lambda関数のログを確認
aws logs tail "/aws/lambda/$FUNCTION_NAME" \
  --since 5m \
  --region us-west-2

# 3. 環境変数が設定されているか
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region us-west-2 \
  --query 'Environment.Variables' | jq
```

#### よくある原因

- Webhook URLが間違っている
- LINE_CHANNEL_SECRETが設定されていない
- 署名検証エラー

### 2. Botが応答しない

#### 確認項目

```bash
# 1. AgentCore Runtimeのログを確認
aws logs tail "/aws/bedrock-agentcore/runtimes/${RUNTIME_ID}-DEFAULT" \
  --since 5m \
  --region us-west-2

# 2. Lambda関数のエラーログ
aws logs tail "/aws/lambda/$FUNCTION_NAME" \
  --since 5m \
  --region us-west-2 \
  --filter-pattern "ERROR"

# 3. IAM権限を確認
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --region us-west-2
```

#### よくある原因

- LINE_CHANNEL_ACCESS_TOKENが設定されていない
- AgentCore Runtimeへのアクセス権限がない
- Bedrockモデルへのアクセス権限がない

### 3. セッションが維持されない

#### 確認項目

```bash
# 1. DynamoDBテーブルの状態
aws dynamodb describe-table \
  --table-name LineAgentSessions \
  --region us-west-2

# 2. セッションデータを確認
aws dynamodb scan \
  --table-name LineAgentSessions \
  --region us-west-2

# 3. Lambda関数のDynamoDB権限を確認
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region us-west-2 \
  --query 'Role'
```

#### よくある原因

- DynamoDBへの書き込み権限がない
- TTLが短すぎる
- セッションIDの生成エラー

### 4. 502 Bad Gateway エラー

#### 確認項目

```bash
# Lambda関数のタイムアウト設定
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region us-west-2 \
  --query 'Timeout'

# 最新のエラーログ
aws logs tail "/aws/lambda/$FUNCTION_NAME" \
  --since 5m \
  --region us-west-2 | grep -A 10 "ERROR"
```

#### よくある原因

- Lambda関数のタイムアウト（30秒）
- 依存関係のインポートエラー
- AgentCore Runtimeの応答遅延

---

## パフォーマンス監視

### CloudWatch Metrics

#### Lambda関数のメトリクス

```bash
# 実行回数
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
  --start-time $(date -u -d '1 hour ago' --iso-8601=seconds) \
  --end-time $(date -u --iso-8601=seconds) \
  --period 300 \
  --statistics Sum \
  --region us-west-2

# エラー率
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
  --start-time $(date -u -d '1 hour ago' --iso-8601=seconds) \
  --end-time $(date -u --iso-8601=seconds) \
  --period 300 \
  --statistics Sum \
  --region us-west-2

# 実行時間
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
  --start-time $(date -u -d '1 hour ago' --iso-8601=seconds) \
  --end-time $(date -u --iso-8601=seconds) \
  --period 300 \
  --statistics Average,Maximum \
  --region us-west-2
```

### コスト監視

```bash
# Lambda実行回数とコスト概算
INVOCATIONS=$(aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
  --start-time $(date -u -d '24 hours ago' --iso-8601=seconds) \
  --end-time $(date -u --iso-8601=seconds) \
  --period 86400 \
  --statistics Sum \
  --region us-west-2 \
  --query 'Datapoints[0].Sum' \
  --output text)

echo "過去24時間の実行回数: $INVOCATIONS"
echo "概算コスト（Lambda）: \$$(echo "scale=4; $INVOCATIONS * 0.0000002" | bc)"
```

---

## 便利なスクリプト

### 全体の状態確認

```bash
#!/bin/bash
# scripts/check-status.sh

echo "=== CloudFormation Stack ==="
aws cloudformation describe-stacks \
  --stack-name CdkAgentcoreStack \
  --region us-west-2 \
  --query 'Stacks[0].StackStatus' \
  --output text

echo -e "\n=== Lambda Function ==="
FUNCTION_NAME=$(aws lambda list-functions \
  --region us-west-2 \
  --query "Functions[?starts_with(FunctionName, 'CdkAgentcoreStack-LineBotWebhookHandler')].FunctionName" \
  --output text)
echo "Function: $FUNCTION_NAME"

aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region us-west-2 \
  --query '{Runtime:Runtime,Memory:MemorySize,Timeout:Timeout,LastModified:LastModified}' \
  --output table

echo -e "\n=== DynamoDB Table ==="
aws dynamodb describe-table \
  --table-name LineAgentSessions \
  --region us-west-2 \
  --query 'Table.{Status:TableStatus,ItemCount:ItemCount}' \
  --output table

echo -e "\n=== Recent Logs (Last 5 minutes) ==="
aws logs tail "/aws/lambda/$FUNCTION_NAME" \
  --since 5m \
  --region us-west-2 | tail -20
```

### ログのエクスポート

```bash
#!/bin/bash
# scripts/export-logs.sh

FUNCTION_NAME=$(aws lambda list-functions \
  --region us-west-2 \
  --query "Functions[?starts_with(FunctionName, 'CdkAgentcoreStack-LineBotWebhookHandler')].FunctionName" \
  --output text)

OUTPUT_FILE="logs-$(date +%Y%m%d-%H%M%S).txt"

aws logs tail "/aws/lambda/$FUNCTION_NAME" \
  --since 1h \
  --region us-west-2 > "$OUTPUT_FILE"

echo "ログを $OUTPUT_FILE に保存しました"
```

---

## 参考リンク

- [AWS Lambda Monitoring](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-functions.html)
- [CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html)
- [DynamoDB Monitoring](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/monitoring-cloudwatch.html)
- [LINE Messaging API Debugging](https://developers.line.biz/ja/docs/messaging-api/debugging/)
