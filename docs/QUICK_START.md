# クイックスタートガイド

このガイドでは、LINE BotとAgentCore Runtimeを連携させるための最短手順を説明します。

## 前提条件

- ✅ AWS CLIが設定済み
- ✅ direnvがインストール済み
- ✅ CDKスタックがデプロイ済み
- ✅ LINE Developers Consoleでチャネルが作成済み

## セットアップ手順（5分）

### 1. LINE認証情報を設定

対話形式のスクリプトを実行：

```bash
./scripts/setup-line-credentials.sh
```

プロンプトに従って以下を入力：
- Channel ID
- Channel Secret  
- Channel Access Token

### 2. Lambda関数に環境変数を設定

```bash
./scripts/update-lambda-env.sh
```

このスクリプトは自動的に：
- CloudFormationスタックから必要な情報を取得
- Lambda関数の環境変数を更新
- 設定内容を表示（トークンは一部マスク）

### 3. LINE Webhook URLを設定

1. [LINE Developers Console](https://developers.line.biz/console/) を開く
2. チャネルの「Messaging API設定」タブを選択
3. 「Webhook URL」に以下を設定：

```bash
# CDKデプロイ時の出力値を確認
cd cdk-agentcore
uv run cdk deploy --outputs-file outputs.json
cat outputs.json | grep LineBotWebhookUrl
```

4. 「検証」ボタンをクリックして接続確認
5. 「Webhookの利用」をONにする

### 4. 応答設定を変更

LINE Developers Consoleで：
1. 「Messaging API設定」タブの下部
2. 「応答メッセージ」を「オフ」に設定
3. 「あいさつメッセージ」も「オフ」に設定（任意）

### 5. Botを友だち追加してテスト

1. LINE Developers Consoleの「Messaging API設定」タブ
2. QRコードをスマートフォンのLINEアプリでスキャン
3. 友だち追加
4. メッセージを送信：

```
こんにちは！
```

5. Botから応答が返ってくることを確認 🎉

## トラブルシューティング

### 環境変数が読み込まれない

```bash
# direnvの状態を確認
direnv status

# 再度許可
direnv allow

# 環境変数を確認
env | grep LINE_
```

### Lambda関数が見つからない

```bash
# デプロイされているか確認
cd cdk-agentcore
uv run cdk list

# スタックの状態を確認
aws cloudformation describe-stacks \
  --stack-name CdkAgentcoreStack \
  --region us-west-2
```

### Webhook検証が失敗する

```bash
# Lambda関数のログを確認
aws logs tail /aws/lambda/CdkAgentcoreStack-LineBotWebhookHandler* \
  --follow --region us-west-2
```

### メッセージに応答がない

1. CloudWatch Logsでエラーを確認
2. 環境変数が正しく設定されているか確認：

```bash
aws lambda get-function-configuration \
  --function-name $(aws lambda list-functions \
    --region us-west-2 \
    --query "Functions[?starts_with(FunctionName, 'CdkAgentcoreStack-LineBotWebhookHandler')].FunctionName" \
    --output text) \
  --region us-west-2 \
  --query 'Environment.Variables'
```

## 次のステップ

- [LINE認証情報のローカル設定ガイド](LINE_CREDENTIALS_SETUP.md) - 詳細な設定方法
- [LINE Bot セットアップガイド](LINE_SETUP.md) - 完全なセットアップ手順
- [アーキテクチャドキュメント](../ARCHITECTURE.md) - システム構成の理解

## よくある質問

### Q: Channel IDとChannel Secretの違いは？

- **Channel ID**: チャネルを識別する公開ID（数字のみ）
- **Channel Secret**: 署名検証に使用する秘密鍵（英数字）
- **Channel Access Token**: LINE APIを呼び出すための認証トークン（長い文字列）

### Q: トークンを再発行したら？

1. `.envrc`ファイルを更新
2. `direnv allow`を実行
3. `./scripts/update-lambda-env.sh`を再実行

### Q: 複数の環境（開発/本番）を管理したい

direnvの環境別設定を使用：

```bash
# 開発環境
cp .envrc .envrc.dev
# 本番環境  
cp .envrc .envrc.prod

# 使用時
ln -sf .envrc.dev .envrc
direnv allow
```

### Q: セキュリティは大丈夫？

- ✅ `.envrc`は`.gitignore`に含まれているのでGitにコミットされません
- ✅ トークンはLambda環境変数として暗号化されて保存されます
- ✅ 署名検証により不正なリクエストを拒否します
- 💡 本番環境ではAWS Secrets Managerの使用を推奨

## サポート

問題が解決しない場合は、以下を確認してください：

1. [トラブルシューティングガイド](LINE_SETUP.md#トラブルシューティング)
2. CloudWatch Logsのエラーメッセージ
3. LINE Developers Consoleのエラー表示
