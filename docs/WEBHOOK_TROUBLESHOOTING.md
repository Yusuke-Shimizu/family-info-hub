# LINE Webhook トラブルシューティング

## Webhook検証が失敗する場合

### 1. Webhook URLの確認

正しいURLが設定されているか確認：

```bash
aws cloudformation describe-stacks \
  --stack-name CdkAgentcoreStack \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`LineBotWebhookUrl`].OutputValue' \
  --output text
```

出力例：
```
https://vrtk62lqzlkifneffjlmtegxde0gztkm.lambda-url.us-west-2.on.aws/
```

### 2. Lambda関数の環境変数を確認

```bash
aws lambda get-function-configuration \
  --function-name $(aws lambda list-functions \
    --region us-west-2 \
    --query "Functions[?starts_with(FunctionName, 'CdkAgentcoreStack-LineBotWebhookHandler')].FunctionName" \
    --output text) \
  --region us-west-2 \
  --query 'Environment.Variables'
```

以下が設定されているか確認：
- `LINE_CHANNEL_ID`
- `LINE_CHANNEL_SECRET`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `AGENT_RUNTIME_ARN`
- `SESSION_TABLE_NAME`

### 3. Lambda関数のログを確認

リアルタイムでログを監視：

```bash
aws logs tail /aws/lambda/$(aws lambda list-functions \
  --region us-west-2 \
  --query "Functions[?starts_with(FunctionName, 'CdkAgentcoreStack-LineBotWebhookHandler')].FunctionName" \
  --output text) \
  --region us-west-2 \
  --follow
```

### 4. 手動でWebhook URLをテスト

署名なしでテスト（401が返ればOK）：

```bash
curl -X POST https://YOUR_WEBHOOK_URL/ \
  -H "Content-Type: application/json" \
  -d '{"events":[]}' \
  -w "\nHTTP Status: %{http_code}\n"
```

期待される結果：
```
{"error": "Missing signature"}
HTTP Status: 401
```

### 5. LINE Developers Consoleでの確認事項

#### Webhook設定
- [ ] Webhook URLが正しく入力されている
- [ ] 末尾に`/`が含まれている
- [ ] 「Webhookの利用」がONになっている

#### 応答設定
- [ ] 「応答メッセージ」がOFFになっている
- [ ] 「あいさつメッセージ」がOFFになっている（推奨）

#### チャネル設定
- [ ] Channel Secretが正しい
- [ ] Channel Access Tokenが発行されている
- [ ] Channel Access Tokenが有効期限内

### 6. よくあるエラーと対処法

#### エラー: "Invalid signature"

**原因**: Channel Secretが間違っている

**対処法**:
1. LINE Developers Consoleで正しいChannel Secretを確認
2. `.envrc`を更新
3. `direnv allow`を実行
4. `./scripts/update-lambda-env.sh`を実行

#### エラー: "Missing signature"

**原因**: LINEからのリクエストに署名ヘッダーがない（通常は問題なし）

**対処法**: LINE Developers Consoleから「検証」ボタンを押す

#### エラー: Lambda関数がタイムアウト

**原因**: AgentCore Runtimeへの接続に時間がかかっている

**対処法**:
1. AgentCore Runtimeが正常に動作しているか確認
2. Lambda関数のタイムアウト設定を確認（現在: 30秒）

```bash
aws lambda get-function-configuration \
  --function-name YOUR_FUNCTION_NAME \
  --region us-west-2 \
  --query 'Timeout'
```

#### エラー: DynamoDBアクセスエラー

**原因**: IAMロールの権限不足

**対処法**: CDKスタックを再デプロイ

```bash
cd cdk-agentcore
uv run cdk deploy
```

### 7. デバッグ用のテストスクリプト

統合テストを実行して動作確認：

```bash
cd line-bot-lambda

# Channel Secretを環境変数に設定
export LINE_CHANNEL_SECRET="YOUR_CHANNEL_SECRET"

# 統合テストを実行
uv run pytest tests/test_integration.py -v -s
```

### 8. LINE側のエラーメッセージ

#### "接続できませんでした"

- Lambda Function URLが正しいか確認
- Lambda関数がデプロイされているか確認
- リージョンが正しいか確認（us-west-2）

#### "検証に失敗しました"

- Lambda関数のログを確認
- 署名検証ロジックを確認
- Channel Secretが正しいか確認

#### "タイムアウトしました"

- Lambda関数の実行時間を確認
- AgentCore Runtimeの応答時間を確認
- ネットワーク接続を確認

### 9. 正常に動作している場合の確認方法

1. **Webhook検証が成功**
   - LINE Developers Consoleで「検証」ボタンを押す
   - 「成功しました」と表示される

2. **Botを友だち追加**
   - QRコードをスキャン
   - 友だち追加完了

3. **メッセージを送信**
   - Botにメッセージを送信
   - 応答が返ってくる

4. **ログを確認**
   ```bash
   aws logs tail /aws/lambda/YOUR_FUNCTION_NAME \
     --region us-west-2 \
     --since 5m
   ```
   
   以下のようなログが出力される：
   ```
   Received message from USER_ID: こんにちは
   Using existing session: SESSION_ID
   Replied: こんにちは！元気ですよ。
   ```

### 10. サポート情報

問題が解決しない場合は、以下の情報を収集してください：

1. Lambda関数のログ（過去30分）
2. LINE Developers Consoleのエラーメッセージ
3. Webhook URLの確認結果
4. 環境変数の設定内容（トークンは除く）
5. CDKスタックのデプロイ状態

```bash
# 情報収集スクリプト
echo "=== Lambda Function ==="
aws lambda list-functions --region us-west-2 \
  --query "Functions[?starts_with(FunctionName, 'CdkAgentcoreStack-LineBotWebhookHandler')].[FunctionName,Runtime,Timeout]" \
  --output table

echo "=== CloudFormation Stack ==="
aws cloudformation describe-stacks \
  --stack-name CdkAgentcoreStack \
  --region us-west-2 \
  --query 'Stacks[0].[StackStatus,LastUpdatedTime]' \
  --output table

echo "=== Recent Logs ==="
aws logs tail /aws/lambda/$(aws lambda list-functions \
  --region us-west-2 \
  --query "Functions[?starts_with(FunctionName, 'CdkAgentcoreStack-LineBotWebhookHandler')].FunctionName" \
  --output text) \
  --region us-west-2 \
  --since 30m
```

## 参考リンク

- [LINE Messaging API ドキュメント](https://developers.line.biz/ja/docs/messaging-api/)
- [Webhook設定](https://developers.line.biz/ja/docs/messaging-api/receiving-messages/)
- [署名検証](https://developers.line.biz/ja/reference/messaging-api/#signature-validation)
