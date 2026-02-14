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
                "AWS_DEFAULT_REGION": self.region
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
                "LINE_CHANNEL_ACCESS_TOKEN": "",  # デプロイ後に手動設定
                "LINE_CHANNEL_SECRET": "",  # デプロイ後に手動設定
                "AGENT_RUNTIME_ARN": runtime.agent_runtime_arn,
                "SESSION_TABLE_NAME": session_table.table_name,
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
                resources=[runtime.agent_runtime_arn]
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
