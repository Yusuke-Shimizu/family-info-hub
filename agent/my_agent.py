import os
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

# デフォルトリージョンを設定
os.environ.setdefault("AWS_DEFAULT_REGION", "us-west-2")

app = BedrockAgentCoreApp()

# シンプルなエージェントを作成（デフォルトでClaude 4 Sonnetを使用）
agent = Agent()


@app.entrypoint
def invoke(payload, context=None):
    """エージェントのエントリーポイント"""
    user_message = payload.get("prompt", "こんにちは！")
    
    # エージェントを実行
    result = agent(user_message)
    
    return {"result": result.message}


if __name__ == "__main__":
    # ローカルでテスト実行（ポート8080で起動）
    print("Starting agent on http://localhost:8080")
    app.run()


