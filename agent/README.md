# Simple Strands Agent

シンプルなStrands Agentの実装です。

## セットアップ

```bash
# 依存関係のインストール
uv sync
```

## ローカルテスト

```bash
# エージェントをローカルで起動
uv run python my_agent.py
```

別のターミナルで：

```bash
# エージェントをテスト
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "こんにちは！"}'
```

## AgentCore Runtimeへのデプロイ

```bash
# bedrock-agentcore-starter-toolkitのインストール
uv add bedrock-agentcore-starter-toolkit

# エージェントの設定
uv run agentcore configure -e my_agent.py

# デプロイ
uv run agentcore deploy

# テスト
uv run agentcore invoke '{"prompt": "こんにちは！"}'

# クリーンアップ
uv run agentcore destroy
```

## エージェントの説明

このエージェントは：
- 親切なアシスタントとして動作
- ユーザーの質問に簡潔に答える
- Bedrock上のClaude Sonnet 4.0を使用
