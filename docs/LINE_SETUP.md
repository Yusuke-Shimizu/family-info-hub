# LINE Messaging API セットアップガイド

## 1. LINE Developers アカウント作成

1. [LINE Developers Console](https://developers.line.biz/console/) にアクセス
2. LINEアカウントでログイン
3. 初回の場合は開発者登録を完了

## 2. プロバイダーの作成

1. LINE Developers Consoleのトップページで「作成」をクリック
2. 「プロバイダーを作成」を選択
3. プロバイダー名を入力（例：`MyCompany`）
4. 「作成」をクリック

## 3. Messaging API チャネルの作成

1. 作成したプロバイダーを選択
2. 「新規チャネル作成」をクリック
3. 「Messaging API」を選択
4. 以下の情報を入力：
   - **チャネル名**: `Family Info Hub Bot`（任意の名前）
   - **チャネル説明**: `AgentCore Runtime連携ボット`
   - **大業種**: 適切なカテゴリを選択
   - **小業種**: 適切なカテゴリを選択
   - **メールアドレス**: 連絡先メールアドレス
5. 利用規約に同意して「作成」をクリック

## 4. Channel Access Token の取得

1. 作成したチャネルを選択
2. 「Messaging API設定」タブをクリック
3. 「チャネルアクセストークン（長期）」セクションまでスクロール
4. 「発行」ボタンをクリック
5. 表示されたトークンをコピー（後で使用）

```
例: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...（長い文字列）
```

⚠️ **重要**: このトークンは一度しか表示されないので、必ず安全な場所に保存してください。

## 5. Channel Secret の取得

1. 同じチャネルの「チャネル基本設定」タブをクリック
2. 「チャネルシークレット」をコピー

```
例: 1234567890abcdef1234567890abcdef
```

## 6. Webhook URL の設定

1. 「Messaging API設定」タブに戻る
2. 「Webhook設定」セクションを見つける
3. 「Webhook URL」に以下を入力：

```
https://vrtk62lqzlkifneffjlmtegxde0gztkm.lambda-url.us-west-2.on.aws/
```

（CDKデプロイ時の`LineBotWebhookUrl`出力値を使用）

4. 「更新」をクリック
5. 「検証」ボタンをクリックして接続を確認
6. 「Webhookの利用」をONにする

## 7. 応答設定

1. 「Messaging API設定」タブの下部にある「LINE公式アカウント機能」セクション
2. 「応答メッセージ」を「オフ」に設定（Botが自動応答するため）
3. 「あいさつメッセージ」も「オフ」に設定（任意）

## 8. Lambda環境変数の設定

取得した認証情報をLambda関数に設定します：

### 方法1: AWS CLIで設定

```bash
# 推奨: スクリプトを使用
./scripts/update-lambda-env.sh

# または手動で設定（Lambda関数名とARNは実際の値に置き換えてください）
aws lambda update-function-configuration \
  --function-name YOUR_LAMBDA_FUNCTION_NAME \
  --environment "Variables={
    LINE_CHANNEL_ACCESS_TOKEN=YOUR_CHANNEL_ACCESS_TOKEN,
    LINE_CHANNEL_SECRET=YOUR_CHANNEL_SECRET,
    AGENT_RUNTIME_ARN=YOUR_AGENT_RUNTIME_ARN,
    SESSION_TABLE_NAME=LineAgentSessions
  }" \
  --region us-west-2
```

### 方法2: AWS Consoleで設定

1. [Lambda Console](https://console.aws.amazon.com/lambda/) を開く
2. `CdkAgentcoreStack-LineBotWebhookHandler...` という名前の関数を選択
3. 「設定」タブ → 「環境変数」を選択
4. 「編集」をクリック
5. 以下の環境変数を更新：
   - `LINE_CHANNEL_ACCESS_TOKEN`: 取得したChannel Access Token
   - `LINE_CHANNEL_SECRET`: 取得したChannel Secret
6. 「保存」をクリック

## 9. 動作確認

### LINE公式アカウントを友だち追加

1. LINE Developers Consoleの「Messaging API設定」タブ
2. 「QRコード」をスマートフォンのLINEアプリでスキャン
3. 友だち追加

### メッセージを送信してテスト

1. 追加したBotにメッセージを送信：
   ```
   こんにちは！
   ```

2. Botから応答が返ってくることを確認

3. 会話を続けてセッションが維持されることを確認：
   ```
   What is 10 + 5?
   ```
   ```
   What was my previous question?
   ```

## 10. 統合テストの実行

環境変数を設定したら、統合テストを実行できます：

```bash
cd line-bot-lambda

# Channel Secretを環境変数に設定
export LINE_CHANNEL_SECRET="YOUR_CHANNEL_SECRET"

# 統合テストを実行
uv run pytest tests/test_integration.py -v -s
```

## トラブルシューティング

### Webhook検証が失敗する場合

1. Lambda関数のログを確認：
   ```bash
   # Lambda関数名を取得
   FUNCTION_NAME=$(aws lambda list-functions \
     --region us-west-2 \
     --query "Functions[?starts_with(FunctionName, 'CdkAgentcoreStack-LineBotWebhookHandler')].FunctionName" \
     --output text)
   
   # ログを確認
   aws logs tail /aws/lambda/$FUNCTION_NAME --follow --region us-west-2
   ```

2. 環境変数が正しく設定されているか確認：
   ```bash
   aws lambda get-function-configuration \
     --function-name $FUNCTION_NAME \
     --region us-west-2 \
     --query 'Environment.Variables'
   ```

### メッセージに応答がない場合

1. CloudWatch Logsでエラーを確認
2. AgentCore Runtimeが正常に動作しているか確認
3. DynamoDBテーブルにセッションが保存されているか確認：
   ```bash
   aws dynamodb scan --table-name LineAgentSessions --region us-west-2
   ```

### 署名検証エラーが出る場合

- Channel Secretが正しく設定されているか確認
- Webhook URLが正しいか確認（末尾の`/`を含む）

## セキュリティのベストプラクティス

1. **Channel Access Tokenは絶対に公開しない**
   - GitHubなどにコミットしない
   - 環境変数として管理
   - AWS Secrets Managerの使用を検討

2. **定期的にトークンをローテーション**
   - LINE Developers Consoleで再発行可能

3. **Webhook URLはHTTPSのみ**
   - Lambda Function URLは自動的にHTTPS

4. **署名検証を必ず実装**
   - 実装済み（`verify_signature`関数）

## 参考リンク

- [LINE Messaging API ドキュメント](https://developers.line.biz/ja/docs/messaging-api/)
- [LINE Developers Console](https://developers.line.biz/console/)
- [Messaging API リファレンス](https://developers.line.biz/ja/reference/messaging-api/)
