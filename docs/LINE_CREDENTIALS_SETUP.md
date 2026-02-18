# LINE認証情報のローカル設定ガイド

## 概要

このガイドでは、LINE Messaging APIの認証情報をdirenvを使ってローカルで管理し、コマンドでLambda関数に設定する方法を説明します。

## セットアップフロー

```
┌─────────────────────────────────────────────────────────────┐
│ 1. LINE Developers Console                                  │
│    ├─ Channel ID を取得                                     │
│    ├─ Channel Secret を取得                                 │
│    └─ Channel Access Token を発行                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. ローカル環境 (.envrc)                                    │
│    ./scripts/setup-line-credentials.sh                      │
│    ├─ .envrc ファイルを作成                                 │
│    ├─ 認証情報を入力                                        │
│    └─ direnv allow で環境変数を読み込み                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. AWS Lambda関数                                           │
│    ./scripts/update-lambda-env.sh                           │
│    ├─ CloudFormationから情報を取得                          │
│    ├─ Lambda環境変数を更新                                  │
│    └─ 設定内容を確認                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. LINE Webhook設定                                         │
│    ├─ Webhook URLを設定                                     │
│    ├─ 接続を検証                                            │
│    └─ Webhookを有効化                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. 動作確認                                                 │
│    ├─ Botを友だち追加                                       │
│    └─ メッセージを送信してテスト                            │
└─────────────────────────────────────────────────────────────┘
```

## 前提条件

- direnvがインストールされていること
- AWS CLIが設定されていること
- LINE Developers Consoleでチャネルが作成されていること

## 手順

### クイックセットアップ（推奨）

対話形式のスクリプトを使用して簡単にセットアップできます：

```bash
./scripts/setup-line-credentials.sh
```

このスクリプトは以下を自動的に行います：
1. `.envrc`ファイルの作成
2. 認証情報の入力プロンプト
3. direnvでの環境変数読み込み

### 手動セットアップ

手動で設定する場合は以下の手順に従ってください。

### 1. LINE Developers Consoleから認証情報を取得

#### Channel IDの取得
1. [LINE Developers Console](https://developers.line.biz/console/) にログイン
2. 作成したプロバイダーとチャネルを選択
3. 「チャネル基本設定」タブを開く
4. 「チャネルID」をコピー（例: `1234567890`）

#### Channel Secretの取得
1. 同じ「チャネル基本設定」タブ内
2. 「チャネルシークレット」をコピー（例: `1234567890abcdef1234567890abcdef`）

#### Channel Access Tokenの取得
1. 「Messaging API設定」タブを開く
2. 「チャネルアクセストークン（長期）」セクションまでスクロール
3. 「発行」ボタンをクリック
4. 表示されたトークンをコピー（例: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`）

⚠️ **重要**: トークンは一度しか表示されないので、必ず保存してください。

### 2. .envrcファイルを作成

プロジェクトルートで`.envrc.example`をコピーして`.envrc`を作成：

```bash
cp .envrc.example .envrc
```

### 3. .envrcファイルを編集

取得した認証情報を`.envrc`に設定：

```bash
# LINE Messaging API 認証情報
export LINE_CHANNEL_ID="1234567890"
export LINE_CHANNEL_SECRET="1234567890abcdef1234567890abcdef"
export LINE_CHANNEL_ACCESS_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# AWS設定
export AWS_REGION="us-west-2"
export AWS_PROFILE="default"
```

### 4. direnvで環境変数を読み込む

```bash
direnv allow
```

これで環境変数が自動的に読み込まれます。確認するには：

```bash
echo $LINE_CHANNEL_ID
echo $LINE_CHANNEL_SECRET
# トークンは長いので最初の20文字だけ表示
echo ${LINE_CHANNEL_ACCESS_TOKEN:0:20}
```

### 5. Lambda関数に環境変数を設定

スクリプトを実行してLambda関数に環境変数を設定：

```bash
./scripts/update-lambda-env.sh
```

スクリプトは以下を自動的に行います：
1. 環境変数が設定されているか確認
2. CloudFormationスタックから必要な情報を取得
3. Lambda関数の環境変数を更新
4. 設定内容を表示（トークンは一部マスク）

### 6. 動作確認

#### Webhook URLを設定

1. LINE Developers Consoleの「Messaging API設定」タブ
2. 「Webhook URL」にCDKデプロイ時の出力値を設定
3. 「検証」ボタンをクリックして接続確認
4. 「Webhookの利用」をONにする

#### Botを友だち追加してテスト

1. QRコードをスキャンしてBotを友だち追加
2. メッセージを送信してみる：
   ```
   こんにちは！
   ```
3. Botから応答が返ってくることを確認

## トラブルシューティング

### direnvが環境変数を読み込まない

```bash
# direnvの状態を確認
direnv status

# 再度許可
direnv allow
```

### スクリプト実行時にエラーが出る

```bash
# 環境変数が設定されているか確認
env | grep LINE_

# AWS認証情報を確認
aws sts get-caller-identity

# Lambda関数が存在するか確認
aws lambda list-functions --region us-west-2 | grep LineBotWebhook
```

### Lambda関数の環境変数を確認

```bash
# 現在の設定を確認
aws lambda get-function-configuration \
  --function-name $(aws lambda list-functions \
    --region us-west-2 \
    --query "Functions[?starts_with(FunctionName, 'CdkAgentcoreStack-LineBotWebhookHandler')].FunctionName" \
    --output text) \
  --region us-west-2 \
  --query 'Environment.Variables'
```

## セキュリティのベストプラクティス

1. `.envrc`ファイルは絶対にGitにコミットしない
   - `.gitignore`に含まれていることを確認済み

2. 認証情報を共有しない
   - チームメンバーは各自で取得して設定

3. 定期的にトークンをローテーション
   - LINE Developers Consoleで再発行可能
   - 再発行後は`.envrc`を更新して`./scripts/update-lambda-env.sh`を再実行

4. 本番環境ではAWS Secrets Managerの使用を検討
   - より安全な認証情報管理が可能

## 参考

- [direnv公式ドキュメント](https://direnv.net/)
- [LINE Messaging API ドキュメント](https://developers.line.biz/ja/docs/messaging-api/)
- [AWS Lambda環境変数](https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html)
