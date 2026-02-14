from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct


class CdkAgentcoreStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3バケット: エージェントコードのデプロイ用
        agent_bucket = s3.Bucket(
            self,
            "AgentBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # IAM実行ロール: AgentCore Runtime用
        execution_role = iam.Role(
            self,
            "AgentExecutionRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchLogsFullAccess"
                ),
            ],
        )

        # Bedrock呼び出し権限
        execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-*"
                ],
            )
        )

        # S3読み取り権限
        agent_bucket.grant_read(execution_role)

        # エージェントコードをS3にデプロイ
        s3deploy.BucketDeployment(
            self,
            "DeployAgentCode",
            sources=[s3deploy.Source.asset("../agent")],
            destination_bucket=agent_bucket,
            destination_key_prefix="agent",
        )

        # 出力
        CfnOutput(
            self,
            "AgentBucketName",
            value=agent_bucket.bucket_name,
            description="S3 bucket for agent code",
        )

        CfnOutput(
            self,
            "ExecutionRoleArn",
            value=execution_role.role_arn,
            description="IAM execution role ARN for AgentCore Runtime",
        )
