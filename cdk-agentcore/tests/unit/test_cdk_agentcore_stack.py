import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk_agentcore.cdk_agentcore_stack import CdkAgentcoreStack


def test_s3_bucket_created():
    """S3バケットが作成されることを確認"""
    app = core.App()
    stack = CdkAgentcoreStack(app, "cdk-agentcore")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::S3::Bucket", {
        "Tags": assertions.Match.array_with([
            {"Key": "aws-cdk:auto-delete-objects", "Value": "true"}
        ])
    })


def test_iam_role_created():
    """IAM実行ロールが作成されることを確認"""
    app = core.App()
    stack = CdkAgentcoreStack(app, "cdk-agentcore")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::IAM::Role", {
        "AssumeRolePolicyDocument": {
            "Statement": assertions.Match.array_with([
                assertions.Match.object_like({
                    "Action": "sts:AssumeRole",
                    "Effect": "Allow",
                    "Principal": {"Service": "bedrock.amazonaws.com"}
                })
            ])
        }
    })


def test_bedrock_invoke_policy():
    """Bedrock呼び出しポリシーが設定されることを確認"""
    app = core.App()
    stack = CdkAgentcoreStack(app, "cdk-agentcore")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::IAM::Policy", {
        "PolicyDocument": {
            "Statement": assertions.Match.array_with([
                assertions.Match.object_like({
                    "Action": "bedrock:InvokeModel",
                    "Effect": "Allow"
                })
            ])
        }
    })


def test_outputs_exist():
    """スタック出力が存在することを確認"""
    app = core.App()
    stack = CdkAgentcoreStack(app, "cdk-agentcore")
    template = assertions.Template.from_stack(stack)

    # AgentBucketName出力の確認
    template.has_output("AgentBucketName", {})
    
    # ExecutionRoleArn出力の確認
    template.has_output("ExecutionRoleArn", {})

