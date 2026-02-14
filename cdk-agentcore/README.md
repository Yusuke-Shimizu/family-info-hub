# AgentCore Runtime CDK Stack

AWS CDK (Python) を使用した Amazon Bedrock AgentCore Runtime のインフラストラクチャ構築プロジェクトです。

## 構成

- **IaC**: AWS CDK (Python) + uv
- **Agent Framework**: Strands Agents
- **Runtime**: Amazon Bedrock AgentCore

## 前提条件

- Python 3.10+
- uv (Python package manager)
- AWS CLI (認証設定済み)
- Bedrock でのモデルアクセス (Anthropic Claude Sonnet 4.0)

## セットアップ

```bash
# 依存関係のインストール
uv sync

# CDK Bootstrap (初回のみ)
uv run cdk bootstrap

# スタックの確認
uv run cdk synth
```

## デプロイ

```bash
# デプロイ
uv run cdk deploy

# 差分確認
uv run cdk diff
```

## エージェントのデプロイ

CDKスタックをデプロイ後、エージェントを AgentCore Runtime にデプロイします。

```bash
cd ../agent

# 依存関係のインストール
pip install bedrock-agentcore strands-agents bedrock-agentcore-starter-toolkit

# エージェントの設定
agentcore configure -e my_agent.py

# デプロイ
agentcore deploy

# テスト
agentcore invoke '{"prompt": "Hello!"}'
```

## リソース

デプロイ後、以下のリソースが作成されます：

- S3 バケット: エージェントコード格納用
- IAM ロール: AgentCore Runtime 実行用
- CloudWatch Logs: エージェントログ

## クリーンアップ

```bash
# AgentCore Runtime の削除
cd ../agent
agentcore destroy

# CDKスタックの削除
cd ../cdk-agentcore
uv run cdk destroy
```
