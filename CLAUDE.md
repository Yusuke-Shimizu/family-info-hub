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
# AWS認証情報を確認
aws sts get-caller-identity --profile default

# リージョンを確認
echo $AWS_REGION
```

## 参考

- [MCP公式ドキュメント](https://modelcontextprotocol.io/)
- [AgentCore MCP Server](https://github.com/awslabs/agentcore-mcp-server)
