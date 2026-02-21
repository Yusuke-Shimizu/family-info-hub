import os
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

# デフォルトリージョンを設定
os.environ.setdefault("AWS_DEFAULT_REGION", "us-west-2")

app = BedrockAgentCoreApp()

SYSTEM_PROMPT = """あなたは家族情報ハブのアシスタントです。家族の日常をサポートし、会話の文脈を理解して親身に回答します。

## コンテキストの解釈
プロンプトには以下のセクションが含まれることがあります：
- [過去の長期記憶]: 過去の会話から学習した家族に関する重要情報。これを参考に個別化した回答をしてください。
- [今セッションの会話履歴]: 現在の会話の流れ。この流れを踏まえて回答してください。
- [ユーザーのメッセージ]: 最新のメッセージ。これに対して回答してください。

## 回答スタイル
- 日本語で回答する
- LINEメッセージとして読みやすい適切な長さで回答する（長すぎず短すぎず）
- 関西弁を基本とし、たまに和歌山弁も交えた親しみやすい口調で話す
  - 関西弁の例：「〜やで」「〜やん」「〜やな」「〜してな」「ほんまに」「なんでやねん」
  - 和歌山弁の例：「〜やんか」「〜やけど」「〜しとう」「そうかいな」「ほうか」
- 家族の情報が記憶にある場合は、それを活かした個別化された回答をする"""


@app.entrypoint
def invoke(payload, context=None):
    """エージェントのエントリーポイント"""
    user_message = payload.get("prompt", "こんにちは！")

    # 呼び出しごとに新しいAgentを生成する。
    # グローバルで使い回すと内部会話履歴が全セッション・全ユーザーで混入するため、
    # コンテキストはLambda側がメモリ経由で注入する方式に統一する。
    agent = Agent(model="us.anthropic.claude-sonnet-4-6", system_prompt=SYSTEM_PROMPT)
    result = agent(user_message)

    return {"result": result.message}


if __name__ == "__main__":
    # ローカルでテスト実行（ポート8080で起動）
    print("Starting agent on http://localhost:8080")
    app.run()


