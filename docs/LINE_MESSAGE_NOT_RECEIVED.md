# LINE メッセージが届かない場合のトラブルシューティング

## 症状

- Webhook検証は成功している
- メッセージを送信してもLambda関数にイベントが届かない
- ログに`Processing 0 events`しか表示されない

## 確認事項

### 1. LINE Developers Console > Messaging API設定

#### Webhook設定
- [ ] **Webhook URL**が正しく設定されている
  ```
  https://vrtk62lqzlkifneffjlmtegxde0gztkm.lambda-url.us-west-2.on.aws/
  ```
- [ ] **「Webhookの利用」がON**になっている
  - これがOFFだとメッセージイベントが送信されません

#### 応答設定
- [ ] **「応答メッセージ」がOFF**になっている
  - ONだとLINE公式アカウントの自動応答が優先されます
- [ ] **「あいさつメッセージ」がOFF**になっている（推奨）

### 2. Botの友だち追加

- [ ] QRコードをスキャンして友だち追加している
- [ ] トークルームが開いている
- [ ] ブロックしていない

### 3. メッセージの種類

Lambda関数は以下のメッセージのみ処理します：
- ✅ テキストメッセージ
- ❌ スタンプ
- ❌ 画像
- ❌ 動画
- ❌ 音声
- ❌ 位置情報

テキストメッセージを送信してください。

## デバッグ手順

### ステップ1: Webhook設定を確認

LINE Developers Consoleで：
1. チャネルを選択
2. 「Messaging API設定」タブ
3. 「Webhook設定」セクション
4. 「Webhookの利用」を確認 → **ONにする**

### ステップ2: 応答設定を確認

同じページの下部：
1. 「LINE公式アカウント機能」セクション
2. 「応答メッセージ」を確認 → **OFFにする**

### ステップ3: メッセージを送信

1. LINEアプリでBotのトークルームを開く
2. テキストメッセージを送信（例: 「こんにちは」）
3. 10秒待つ

### ステップ4: ログを確認

```bash
aws logs tail /aws/lambda/CdkAgentcoreStack-LineBotWebhookHandlerD45F4F04-keJTPhu2Dc9V \
  --region us-west-2 \
  --since 1m \
  --format short
```

期待されるログ：
```
Received event: {...}
Signature present: True
Signature verified successfully
Processing 1 events
Event type: message
Received message from U1234567890: こんにちは
Created new session: abc-123-def
Replied: こんにちは！元気ですよ。
```

### ステップ5: リアルタイム監視

別のターミナルで：
```bash
aws logs tail /aws/lambda/CdkAgentcoreStack-LineBotWebhookHandlerD45F4F04-keJTPhu2Dc9V \
  --region us-west-2 \
  --follow
```

メッセージを送信すると、リアルタイムでログが表示されます。

## よくある問題と解決方法

### 問題1: 「Webhookの利用」がOFFになっている

**症状**: メッセージを送信してもログに何も表示されない

**解決方法**:
1. LINE Developers Console > Messaging API設定
2. 「Webhookの利用」をONにする
3. メッセージを再送信

### 問題2: 「応答メッセージ」がONになっている

**症状**: LINE公式アカウントの自動応答が返ってくる

**解決方法**:
1. LINE Developers Console > Messaging API設定
2. 「応答メッセージ」をOFFにする
3. メッセージを再送信

### 問題3: Botをブロックしている

**症状**: メッセージを送信してもログに何も表示されない

**解決方法**:
1. LINEアプリでBotのトークルームを開く
2. 右上のメニュー > 「ブロック解除」
3. メッセージを再送信

### 問題4: 友だち追加していない

**症状**: トークルームが見つからない

**解決方法**:
1. LINE Developers Console > Messaging API設定
2. QRコードをスキャン
3. 友だち追加
4. メッセージを送信

### 問題5: スタンプや画像を送信している

**症状**: ログに`Processing 1 events`と表示されるが、`Received message`が表示されない

**解決方法**:
- テキストメッセージを送信してください
- Lambda関数はテキストメッセージのみ処理します

## 設定確認スクリプト

以下のスクリプトで設定を確認できます：

```bash
#!/bin/bash

echo "=== Lambda関数の確認 ==="
aws lambda get-function-configuration \
  --function-name CdkAgentcoreStack-LineBotWebhookHandlerD45F4F04-keJTPhu2Dc9V \
  --region us-west-2 \
  --query '{FunctionName:FunctionName,Runtime:Runtime,Timeout:Timeout,MemorySize:MemorySize}' \
  --output table

echo ""
echo "=== 環境変数の確認 ==="
aws lambda get-function-configuration \
  --function-name CdkAgentcoreStack-LineBotWebhookHandlerD45F4F04-keJTPhu2Dc9V \
  --region us-west-2 \
  --query 'Environment.Variables' \
  --output json | jq 'keys'

echo ""
echo "=== 最近のログ（過去5分） ==="
aws logs tail /aws/lambda/CdkAgentcoreStack-LineBotWebhookHandlerD45F4F04-keJTPhu2Dc9V \
  --region us-west-2 \
  --since 5m \
  --format short | grep -E "Received message|Event type|Processing|Error" | tail -10

echo ""
echo "=== Webhook URL ==="
aws cloudformation describe-stacks \
  --stack-name CdkAgentcoreStack \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`LineBotWebhookUrl`].OutputValue' \
  --output text
```

## まだ解決しない場合

1. **LINE Developers Consoleのスクリーンショットを確認**
   - Webhook設定
   - 応答設定

2. **Lambda関数のログを全て確認**
   ```bash
   aws logs tail /aws/lambda/CdkAgentcoreStack-LineBotWebhookHandlerD45F4F04-keJTPhu2Dc9V \
     --region us-west-2 \
     --since 10m
   ```

3. **統合テストを実行**
   ```bash
   cd line-bot-lambda
   export LINE_CHANNEL_SECRET="YOUR_CHANNEL_SECRET"
   uv run pytest tests/test_integration.py -v -s
   ```

4. **CDKスタックを再デプロイ**
   ```bash
   cd cdk-agentcore
   uv run cdk deploy
   ```

## 参考リンク

- [LINE Messaging API - Webhookを受信する](https://developers.line.biz/ja/docs/messaging-api/receiving-messages/)
- [LINE Messaging API - 応答メッセージ](https://developers.line.biz/ja/docs/messaging-api/overview/#response-messages)
