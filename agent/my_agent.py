import os
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

# デフォルトリージョンを設定
os.environ.setdefault("AWS_DEFAULT_REGION", "us-west-2")

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context=None):
    """エージェントのエントリーポイント"""
    user_message = payload.get("prompt", "こんにちは！")

    # 呼び出しごとに新しいAgentを生成する。
    # グローバルで使い回すと内部会話履歴が全セッション・全ユーザーで混入するため、
    # コンテキストはLambda側がメモリ経由で注入する方式に統一する。
    agent = Agent(model="us.anthropic.claude-sonnet-4-6")
    result = agent(user_message)

    return {"result": result.message}


if __name__ == "__main__":
    # ローカルでテスト実行（ポート8080で起動）
    print("Starting agent on http://localhost:8080")
    app.run()


