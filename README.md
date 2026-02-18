# family-info-hub

子供に関連する学校や習い事からのプリントやメッセージをまとめて、子供に関する出来事を記憶・管理するAIエージェント

## プロジェクト概要

複数の子供の学校・習い事に関する情報を一元管理し、AIによる要約・整理で家族が必要な情報にすぐアクセスできるシステム。

## 主要機能

### 1. 多様な入力形式に対応
- 📄 **紙のプリント**: 写真撮影してOCR処理
- 💬 **デジタルメッセージ**: メール・LINEなどからの取り込み
- 📎 **ファイル**: PDF・画像ファイルの直接アップロード

### 2. AIによる要約・整理（コア機能）
- 大量の情報から重要ポイントを自動抽出
- 各種プリント・メッセージを構造化して保存
- 自然言語での質問応答
  - 例: "次の遠足はいつ？"
  - 例: "太郎の宿題の提出期限は？"

### 3. 複数子供の管理
- 2人以上の子供の情報を個別に管理
- 子供ごとに学校・習い事の情報を分類
- 兄弟姉妹のスケジュール統合ビュー

### 4. 家族間での情報共有
- 夫婦など複数ユーザーでの共有
- 同期された情報へのアクセス

## 管理対象の情報

- 🏫 **学校関連**
  - お便り・連絡プリント
  - 時間割・行事予定
  - 提出物・宿題の期限
  - PTA活動・保護者会

- 🎨 **習い事関連**
  - レッスンスケジュール
  - 発表会・試合の予定
  - 月謝・費用関連
  - 先生からの連絡

## 技術スタック

- **IaC**: AWS CDK (Python)
- **Agent Framework**: Strands Agents
- **Runtime**: Amazon Bedrock AgentCore
- **LLM**: Claude Sonnet 4.0 on Amazon Bedrock
- **Package Manager**: uv
- **CI/CD**: GitHub Actions

## セットアップガイド

### 開発環境のセットアップ

#### 1. pre-commitフックのインストール（推奨）

シークレット情報の誤コミットを防ぐため、gitleaksをpre-commitフックとして設定：

```bash
# pre-commitをインストール
brew install pre-commit

# または
pip install pre-commit

# pre-commitフックを有効化
pre-commit install
```

これにより、コミット前に自動的にgitleaksがシークレット情報をスキャンします。

#### 2. gitleaksの手動実行

```bash
# Homebrewでインストール
brew install gitleaks

# リポジトリ全体をスキャン
gitleaks detect --verbose

# 特定のファイルをスキャン
gitleaks detect --source . --verbose
```

### クイックスタート

最短5分でLINE Botをセットアップ：
- [クイックスタートガイド](docs/QUICK_START.md) - 最短手順でセットアップ

### GitHub Actions セットアップ

GitHub ActionsでAWS OIDCを使用するため、以下のSecretを設定してください：

1. GitHubリポジトリの Settings > Secrets and variables > Actions
2. 以下のSecretを追加：
   - `AWS_ROLE_ARN`: GitHub Actions用のIAMロールARN
     - 例: `arn:aws:iam::YOUR_ACCOUNT_ID:role/GitHubActionsRole`

### LINE Bot セットアップ

LINE Messaging APIの認証情報をローカルで管理し、Lambda関数に設定する方法：

1. **認証情報の取得**: [LINE認証情報のローカル設定ガイド](docs/LINE_CREDENTIALS_SETUP.md)を参照
2. **direnvで環境変数を設定**: `.envrc.example`をコピーして`.envrc`を作成
3. **Lambda関数に反映**: `./scripts/update-lambda-env.sh`を実行

詳細は以下のドキュメントを参照：
- [LINE認証情報のローカル設定ガイド](docs/LINE_CREDENTIALS_SETUP.md)
- [LINE Bot セットアップガイド](docs/LINE_SETUP.md)

## 開発状況

現在は要件定義フェーズ
