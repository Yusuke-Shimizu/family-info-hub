import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk_agentcore.cdk_agentcore_stack import CdkAgentcoreStack


def test_agentcore_runtime_created():
    """AgentCore Runtimeが作成されることを確認"""
    app = core.App()
    stack = CdkAgentcoreStack(app, "cdk-agentcore")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::BedrockAgentCore::Runtime", {
        "ProtocolConfiguration": "HTTP",
        "AgentRuntimeName": "my_agent"
    })


def test_execution_role_created():
    """実行ロールが作成されることを確認"""
    app = core.App()
    stack = CdkAgentcoreStack(app, "cdk-agentcore")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::IAM::Role", {
        "AssumeRolePolicyDocument": {
            "Statement": assertions.Match.array_with([
                assertions.Match.object_like({
                    "Action": "sts:AssumeRole",
                    "Effect": "Allow",
                    "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}
                })
            ])
        }
    })


def test_outputs_exist():
    """スタック出力が存在することを確認"""
    app = core.App()
    stack = CdkAgentcoreStack(app, "cdk-agentcore")
    template = assertions.Template.from_stack(stack)

    # AgentRuntimeId出力の確認
    template.has_output("AgentRuntimeId", {})
    
    # AgentRuntimeArn出力の確認
    template.has_output("AgentRuntimeArn", {})
    
    # AgentRoleArn出力の確認
    template.has_output("AgentRoleArn", {})
    
    # LineBotWebhookUrl出力の確認
    template.has_output("LineBotWebhookUrl", {})
    
    # SessionTableName出力の確認
    template.has_output("SessionTableName", {})


def test_dynamodb_table_created():
    """DynamoDBテーブルが作成されることを確認"""
    app = core.App()
    stack = CdkAgentcoreStack(app, "cdk-agentcore")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::DynamoDB::Table", {
        "TableName": "LineAgentSessions",
        "BillingMode": "PAY_PER_REQUEST",
        "TimeToLiveSpecification": {
            "AttributeName": "ttl",
            "Enabled": True
        }
    })


def test_lambda_function_created():
    """Lambda Functionが作成されることを確認"""
    app = core.App()
    stack = CdkAgentcoreStack(app, "cdk-agentcore")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::Lambda::Function", {
        "Runtime": "python3.13",
        "Handler": "lambda_function.lambda_handler",
        "Timeout": 30,
        "MemorySize": 256
    })


def test_lambda_function_url_created():
    """Lambda Function URLが作成されることを確認"""
    app = core.App()
    stack = CdkAgentcoreStack(app, "cdk-agentcore")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::Lambda::Url", {
        "AuthType": "NONE"
    })



