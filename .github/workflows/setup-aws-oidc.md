# GitHub Actions用AWS OIDC設定ガイド

## OIDCを使ったAWS認証の設定方法

### 1. AWS IAMでOIDCプロバイダーを作成

AWS CLIで実行：

```bash
# OIDCプロバイダーを作成
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### 2. IAMロールを作成

信頼ポリシー（trust-policy.json）:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::889119567707:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:Yusuke-Shimizu/family-info-hub:*"
        }
      }
    }
  ]
}
```

ロールを作成：

```bash
# IAMロールを作成
aws iam create-role \
  --role-name GitHubActionsRole \
  --assume-role-policy-document file://trust-policy.json

# Bedrockアクセス権限を付与
aws iam attach-role-policy \
  --role-name GitHubActionsRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
```

### 3. GitHub Actionsワークフローを更新

`.github/workflows/agent-test.yml`を以下のように更新：

```yaml
name: Agent Test

on:
  push:
    branches: [ main ]
    paths:
      - 'agent/**'
      - '.github/workflows/agent-test.yml'
  pull_request:
    branches: [ main ]
    paths:
      - 'agent/**'
      - '.github/workflows/agent-test.yml'

permissions:
  id-token: write
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: arn:aws:iam::889119567707:role/GitHubActionsRole
        aws-region: us-west-2
    
    - name: Install uv
      uses: astral-sh/setup-uv@v5
      with:
        version: "latest"
    
    - name: Set up Python
      run: uv python install 3.13
    
    - name: Install dependencies
      working-directory: ./agent
      run: uv sync --all-extras
    
    - name: Run pytest
      working-directory: ./agent
      run: uv run pytest tests/ -v
```

## 簡易版：Secretsを使う方法（非推奨）

OIDCの設定が難しい場合、一時的にSecretsを使う方法：

1. GitHubリポジトリの Settings > Secrets and variables > Actions
2. 以下のSecretsを追加：
   - `AWS_ACCESS_KEY_ID`: AWSアクセスキーID
   - `AWS_SECRET_ACCESS_KEY`: AWSシークレットアクセスキー

注意：この方法は長期的な認証情報を使うため、セキュリティリスクがあります。

## 推奨：OIDC方式

- 認証情報をGitHubに保存する必要がない
- 一時的な認証情報を使用
- より安全
- AWSのベストプラクティス
