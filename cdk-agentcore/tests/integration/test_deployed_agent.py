import json
import boto3
import pytest


@pytest.fixture(scope="module")
def agent_runtime_arn():
    """デプロイされたエージェントのARNを取得"""
    cloudformation = boto3.client("cloudformation", region_name="us-west-2")
    
    response = cloudformation.describe_stacks(StackName="CdkAgentcoreStack")
    outputs = response["Stacks"][0]["Outputs"]
    
    for output in outputs:
        if output["OutputKey"] == "AgentRuntimeArn":
            return output["OutputValue"]
    
    pytest.fail("AgentRuntimeArn not found in stack outputs")


@pytest.fixture(scope="module")
def bedrock_client():
    """Bedrock AgentCore クライアントを作成"""
    return boto3.client("bedrock-agentcore", region_name="us-west-2")


def test_agent_basic_response(bedrock_client, agent_runtime_arn):
    """エージェントが基本的な応答を返すことを確認"""
    payload = {"prompt": "Hello! How are you?"}
    
    response = bedrock_client.invoke_agent_runtime(
        agentRuntimeArn=agent_runtime_arn,
        payload=json.dumps(payload).encode("utf-8")
    )
    
    assert response["statusCode"] == 200
    
    result = json.loads(response["response"].read())
    assert "result" in result
    assert "content" in result["result"]
    assert len(result["result"]["content"]) > 0
    assert "text" in result["result"]["content"][0]
    
    # 応答が空でないことを確認
    response_text = result["result"]["content"][0]["text"]
    assert len(response_text) > 0
    print(f"Response: {response_text}")


def test_agent_japanese_response(bedrock_client, agent_runtime_arn):
    """エージェントが日本語で応答できることを確認"""
    payload = {"prompt": "こんにちは！元気ですか？"}
    
    response = bedrock_client.invoke_agent_runtime(
        agentRuntimeArn=agent_runtime_arn,
        payload=json.dumps(payload).encode("utf-8")
    )
    
    assert response["statusCode"] == 200
    
    result = json.loads(response["response"].read())
    response_text = result["result"]["content"][0]["text"]
    assert len(response_text) > 0
    print(f"Response: {response_text}")


def test_agent_calculation(bedrock_client, agent_runtime_arn):
    """エージェントが計算できることを確認"""
    payload = {"prompt": "What is 15 + 27?"}
    
    response = bedrock_client.invoke_agent_runtime(
        agentRuntimeArn=agent_runtime_arn,
        payload=json.dumps(payload).encode("utf-8")
    )
    
    assert response["statusCode"] == 200
    
    result = json.loads(response["response"].read())
    response_text = result["result"]["content"][0]["text"]
    
    # 応答に42が含まれていることを確認
    assert "42" in response_text
    print(f"Response: {response_text}")


def test_agent_multiple_requests(bedrock_client, agent_runtime_arn):
    """複数のリクエストを連続して送信できることを確認"""
    prompts = [
        "What is the capital of France?",
        "What is 10 * 5?",
        "Tell me a fun fact."
    ]
    
    for prompt in prompts:
        payload = {"prompt": prompt}
        
        response = bedrock_client.invoke_agent_runtime(
            agentRuntimeArn=agent_runtime_arn,
            payload=json.dumps(payload).encode("utf-8")
        )
        
        assert response["statusCode"] == 200
        
        result = json.loads(response["response"].read())
        response_text = result["result"]["content"][0]["text"]
        assert len(response_text) > 0
        print(f"Prompt: {prompt}")
        print(f"Response: {response_text}\n")
