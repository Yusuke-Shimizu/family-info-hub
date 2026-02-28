from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    RemovalPolicy,
    BundlingOptions,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_dynamodb as dynamodb,
)
from aws_cdk import aws_bedrock_agentcore_alpha as agentcore
from constructs import Construct
import aws_cdk as core
import os

LINE_SYSTEM_PROMPT = """あなたは家族情報ハブのアシスタントです。家族の日常をサポートし、会話の文脈を理解して親身に回答します。

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
  - 和歌山弁の例：「〜やんか」「〜やけど」「そうかいな」「ほうか」
- 家族の情報が記憶にある場合は、それを活かした個別化された回答をする

## LINEテキストメッセージの書き方ルール
LINEはMarkdownをレンダリングしないため、以下のルールに従うこと：

- **禁止**: `**太字**` `# 見出し` `---` などのMarkdown記法は一切使わない
- **セクション区切り**: 絵文字をヘッダー代わりに使う（例: 📅 日程　🏫 場所　⏰ 時間）
- **箇条書き**: `・` または絵文字で始める（`-` や `*` は使わない）
- **改行**: 適度に空行を入れて読みやすくする
- **強調**: 絵文字や「！」で表現し、`**` は使わない"""


class CdkAgentcoreStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # エージェントのアーティファクトをローカルディレクトリから作成
        agent_runtime_artifact = agentcore.AgentRuntimeArtifact.from_asset("../agent")

        # AgentCore Runtimeを作成
        runtime = agentcore.Runtime(
            self,
            "AgentRuntime",
            runtime_name="my_agent",
            agent_runtime_artifact=agent_runtime_artifact,
            description="Simple Strands agent runtime",
            network_configuration=agentcore.RuntimeNetworkConfiguration.using_public_network(),
            environment_variables={
                "AWS_DEFAULT_REGION": self.region,
                "LINE_SYSTEM_PROMPT": LINE_SYSTEM_PROMPT,
            }
        )

        # Bedrockモデル呼び出し権限を追加
        runtime.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/*",
                    f"arn:aws:bedrock:*:{self.account}:inference-profile/*"
                ]
            )
        )

        # 出力
        CfnOutput(
            self,
            "AgentRuntimeId",
            description="ID of the created agent runtime",
            value=runtime.agent_runtime_id
        )

        CfnOutput(
            self,
            "AgentRuntimeArn",
            description="ARN of the created agent runtime",
            value=runtime.agent_runtime_arn
        )

        CfnOutput(
            self,
            "AgentRoleArn",
            value=runtime.role.role_arn,
            description="IAM role ARN for AgentCore Runtime",
        )

        # DynamoDBテーブル（セッション管理用）
        session_table = dynamodb.Table(
            self,
            "LineAgentSessionTable",
            table_name="LineAgentSessions",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.DESTROY,  # 開発用：本番環境ではRETAINに変更
        )

        # AgentCore Memory（短期・長期記憶）
        memory = agentcore.Memory(self, "FamilyInfoMemory",
            memory_name="family_info_hub",
            description="家族情報ハブのメモリ",
            expiration_duration=Duration.days(90),
            memory_strategies=[
                agentcore.MemoryStrategy.using_semantic(
                    name="FamilyFacts",
                    namespaces=["/family/{actorId}/facts/"],
                ),
                agentcore.MemoryStrategy.using_user_preference(
                    name="FamilyPreferences",
                    namespaces=["/family/{actorId}/preferences/"],
                ),
            ]
        )

        # Lambda Function（LINE Bot Webhook Handler）
        line_bot_lambda = lambda_.Function(
            self,
            "LineBotWebhookHandler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(
                "../line-bot-lambda",
                bundling=core.BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_13.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install --platform manylinux2014_x86_64 --only-binary=:all: -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ],
                )
            ),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "LINE_CHANNEL_ACCESS_TOKEN": os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", ""),
                "LINE_CHANNEL_SECRET": os.environ.get("LINE_CHANNEL_SECRET", ""),
                "AGENT_RUNTIME_ARN": runtime.agent_runtime_arn,
                "SESSION_TABLE_NAME": session_table.table_name,
                "MEMORY_ID": memory.memory_id,
                "LINE_SYSTEM_PROMPT": LINE_SYSTEM_PROMPT,
            }
        )

        # Lambda Function URLを作成
        function_url = line_bot_lambda.add_function_url(
            auth_type=lambda_.FunctionUrlAuthType.NONE,  # LINE署名で保護
        )

        # DynamoDBテーブルへのアクセス権限
        session_table.grant_read_write_data(line_bot_lambda)

        # AgentCore Runtime呼び出し権限
        line_bot_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock-agentcore:InvokeAgentRuntime"],
                resources=[
                    runtime.agent_runtime_arn,
                    f"{runtime.agent_runtime_arn}/*"
                ]
            )
        )

        # AgentCore Memory操作権限
        line_bot_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock-agentcore:CreateEvent",
                    "bedrock-agentcore:ListEvents",
                    "bedrock-agentcore:GetEvent",
                    "bedrock-agentcore:RetrieveMemoryRecords",
                    "bedrock-agentcore:ListMemoryRecords",
                ],
                resources=[
                    f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:memory/{memory.memory_id}",
                    f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:memory/{memory.memory_id}/*",
                ]
            )
        )

        # Bedrock Claude vision（画像分析）呼び出し権限
        # クロスリージョン推論プロファイル(us.*)は内部でfoundation modelにルーティングするため両方必要
        line_bot_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/*",
                    f"arn:aws:bedrock:*:{self.account}:inference-profile/*"
                ]
            )
        )

        # 出力
        CfnOutput(
            self,
            "LineBotWebhookUrl",
            description="LINE Webhook URL (set this in LINE Developers Console)",
            value=function_url.url
        )

        CfnOutput(
            self,
            "SessionTableName",
            description="DynamoDB table name for session management",
            value=session_table.table_name
        )

        CfnOutput(self, "MemoryId",
            description="AgentCore Memory ID",
            value=memory.memory_id
        )
