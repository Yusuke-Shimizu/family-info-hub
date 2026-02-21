# Claude Desktop MCP設定

このプロジェクトでは、Claude DesktopのMCP（Model Context Protocol）を使用してAWS AgentCoreと連携します。

## 設定方法

### 1. Claude Desktop設定ファイルを開く

macOSの場合：
```bash
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### 2. MCP設定を追加

```json
{
  "mcpServers": {
    "agentcore": {
      "command": "uvx",
      "args": ["agentcore-mcp-server"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "default"
      }
    }
  }
}
```

### 3. Claude Desktopを再起動

設定を反映するためにClaude Desktopを再起動してください。

## 使用方法

Claude Desktopで以下のようなプロンプトを使用できます：

```
AgentCore Runtimeにデプロイされているエージェントを呼び出して、
「こんにちは」と挨拶してください
```

## トラブルシューティング

### MCPサーバーが起動しない

```bash
# uvxが正しくインストールされているか確認
which uvx

# agentcore-mcp-serverが利用可能か確認
uvx agentcore-mcp-server --help
```

### AWS認証エラー

```bash
# AWSにログイン（セッション切れの場合はこちらを使用）
aws login

# AWS認証情報を確認
aws sts get-caller-identity --profile default

# リージョンを確認
echo $AWS_REGION
```

## 参考

- [MCP公式ドキュメント](https://modelcontextprotocol.io/)
- [AgentCore MCP Server](https://github.com/awslabs/agentcore-mcp-server)

## AWSコマンド実行のセキュリティポリシー

### 許可するコマンド（参照系のみ）

Claudeが自動実行できるAWS CLIコマンドは以下の参照系に限定する：

- `aws * describe-*` （例: `aws ec2 describe-instances`）
- `aws * list-*` （例: `aws s3api list-buckets`）
- `aws * get-*` （例: `aws iam get-user`）
- `aws * filter-*` （例: `aws ec2 filter-*`）

### 禁止事項

- **更新系・変更系・削除系のAWS CLIコマンドは一切実行しない**
  - `create-*`, `update-*`, `put-*`, `delete-*`, `modify-*` 等は実行禁止
- **秘密情報を含む可能性があるサービスへのアクセスは行わない**
  - AWS Secrets Manager（`aws secretsmanager`）
  - AWS Systems Manager パラメータストア（`aws ssm get-parameter` 等）
  - これらへのアクセスが必要な場合はユーザーに確認を委ねる

### 理由

インシデント分析・調査の大半は参照系コマンドのみで完結できる。
更新系コマンドの誤実行リスクや、秘密情報の意図しない取得を防ぐため、
最小権限の原則に従い参照系のみを自動許可とする。

## テスト・デバッグ・トラブルシューティング

詳細なテスト手順、ログ確認方法、トラブルシューティングガイドは以下を参照：

- [テスト・デバッグ・トラブルシューティングガイド](docs/TESTING_AND_DEBUGGING.md)
