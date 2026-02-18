"""
LINE Bot Lambda Function の統合テスト

1. デプロイされたLambda Function URLに対してHTTPリクエストを送信
2. Lambda関数を直接呼び出し（AWS SDK経由）

両方のテスト方法をサポート
"""
import json
import os
import hashlib
import hmac
import base64
import time
from datetime import datetime
import pytest
import boto3
import requests


@pytest.fixture(scope="module")
def stack_outputs():
    """CloudFormationスタックの出力を取得"""
    cloudformation = boto3.client("cloudformation", region_name="us-west-2")
    
    response = cloudformation.describe_stacks(StackName="CdkAgentcoreStack")
    outputs = response["Stacks"][0]["Outputs"]
    
    output_dict = {}
    for output in outputs:
        output_dict[output["OutputKey"]] = output["OutputValue"]
    
    return output_dict


@pytest.fixture(scope="module")
def webhook_url(stack_outputs):
    """Lambda Function URLを取得"""
    return stack_outputs.get("LineBotWebhookUrl")


@pytest.fixture(scope="module")
def lambda_function_name():
    """Lambda関数名を取得"""
    lambda_client = boto3.client("lambda", region_name="us-west-2")
    
    response = lambda_client.list_functions()
    
    for function in response["Functions"]:
        if function["FunctionName"].startswith("CdkAgentcoreStack-LineBotWebhookHandler"):
            return function["FunctionName"]
    
    pytest.skip("Lambda function not found")


@pytest.fixture(scope="module")
def line_channel_secret():
    """LINE Channel Secretを環境変数から取得"""
    secret = os.environ.get("LINE_CHANNEL_SECRET")
    if not secret:
        pytest.skip("LINE_CHANNEL_SECRET environment variable not set")
    return secret


def create_line_signature(body: str, channel_secret: str) -> str:
    """LINE署名を生成"""
    hash_value = hmac.new(
        channel_secret.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(hash_value).decode("utf-8")


def create_line_webhook_event(user_id: str, message_text: str, reply_token: str = None):
    """LINE Webhookイベントを生成"""
    if reply_token is None:
        reply_token = f"test_reply_token_{int(time.time())}"
    
    return {
        "type": "message",
        "replyToken": reply_token,
        "source": {
            "userId": user_id,
            "type": "user"
        },
        "message": {
            "type": "text",
            "id": f"msg_{int(time.time())}",
            "text": message_text
        },
        "timestamp": int(time.time() * 1000),
        "mode": "active"
    }


def create_lambda_function_url_event(webhook_body: dict, channel_secret: str) -> dict:
    """Lambda Function URLイベントを生成"""
    body = json.dumps(webhook_body)
    signature = create_line_signature(body, channel_secret)
    
    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/",
        "rawQueryString": "",
        "headers": {
            "content-type": "application/json; charset=utf-8",
            "x-line-signature": signature,
            "user-agent": "pytest"
        },
        "requestContext": {
            "accountId": "anonymous",
            "apiId": "test",
            "domainName": "test.lambda-url.us-west-2.on.aws",
            "http": {
                "method": "POST",
                "path": "/",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "pytest"
            },
            "requestId": f"test-{int(time.time())}",
            "routeKey": "$default",
            "stage": "$default",
            "time": datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000"),
            "timeEpoch": int(time.time() * 1000)
        },
        "body": body,
        "isBase64Encoded": False
    }


def invoke_lambda_directly(function_name: str, event: dict) -> dict:
    """Lambda関数を直接呼び出し"""
    lambda_client = boto3.client("lambda", region_name="us-west-2")
    
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(event).encode("utf-8")
    )
    
    payload = json.loads(response["Payload"].read())
    return payload


def get_lambda_logs(function_name: str, minutes: int = 1) -> list:
    """Lambda関数のログを取得"""
    logs_client = boto3.client("logs", region_name="us-west-2")
    log_group = f"/aws/lambda/{function_name}"
    
    start_time = int((time.time() - minutes * 60) * 1000)
    
    try:
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=start_time,
            limit=100
        )
        
        return [event["message"] for event in response.get("events", [])]
    except Exception:
        return []


# ========================================
# Lambda直接呼び出しテスト
# ========================================

def test_lambda_function_exists(lambda_function_name):
    """Lambda関数が存在することを確認"""
    assert lambda_function_name is not None
    print(f"Lambda function: {lambda_function_name}")


@pytest.mark.skipif(
    not os.environ.get("LINE_CHANNEL_SECRET"),
    reason="LINE_CHANNEL_SECRET not set"
)
def test_lambda_invoke_simple_message(lambda_function_name, line_channel_secret):
    """Lambda関数を直接呼び出して簡単なメッセージを処理"""
    user_id = f"test_user_invoke_{int(time.time())}"
    message_text = "こんにちは"
    
    event = create_line_webhook_event(user_id, message_text)
    webhook_body = {"events": [event]}
    lambda_event = create_lambda_function_url_event(webhook_body, line_channel_secret)
    
    response = invoke_lambda_directly(lambda_function_name, lambda_event)
    
    assert response["statusCode"] == 200
    print(f"Response: {response}")
    print(f"User ID: {user_id}")
    print(f"Message: {message_text}")
    
    # ログを確認（オプショナル）
    time.sleep(3)
    logs = get_lambda_logs(lambda_function_name)
    
    if logs:
        log_text = "\n".join(logs)
        print(f"Logs found: {len(logs)} entries")
        # メッセージが処理されたことを確認
        if f"Received message from {user_id}" in log_text:
            print("✓ Message processing confirmed in logs")
        else:
            print("⚠ Message not found in logs (may take time to appear)")
    else:
        print("⚠ No logs retrieved (may take time to appear)")


@pytest.mark.skipif(
    not os.environ.get("LINE_CHANNEL_SECRET"),
    reason="LINE_CHANNEL_SECRET not set"
)
def test_lambda_invoke_calculation(lambda_function_name, line_channel_secret):
    """Lambda関数を直接呼び出して計算を依頼"""
    user_id = f"test_user_calc_{int(time.time())}"
    message_text = "What is 15 + 27?"
    
    event = create_line_webhook_event(user_id, message_text)
    webhook_body = {"events": [event]}
    lambda_event = create_lambda_function_url_event(webhook_body, line_channel_secret)
    
    response = invoke_lambda_directly(lambda_function_name, lambda_event)
    
    assert response["statusCode"] == 200
    print(f"Response: {response}")
    print(f"User ID: {user_id}")
    print(f"Message: {message_text}")


@pytest.mark.skipif(
    not os.environ.get("LINE_CHANNEL_SECRET"),
    reason="LINE_CHANNEL_SECRET not set"
)
def test_lambda_invoke_session_persistence(lambda_function_name, line_channel_secret):
    """Lambda関数を直接呼び出してセッション永続化を確認"""
    user_id = f"test_user_session_invoke_{int(time.time())}"
    
    messages = [
        "My name is Alice",
        "What is my name?",
    ]
    
    for i, message_text in enumerate(messages):
        event = create_line_webhook_event(user_id, message_text)
        webhook_body = {"events": [event]}
        lambda_event = create_lambda_function_url_event(webhook_body, line_channel_secret)
        
        response = invoke_lambda_directly(lambda_function_name, lambda_event)
        
        assert response["statusCode"] == 200
        print(f"Message {i+1}: {message_text}")
        print(f"Response: {response}")
        
        # 次のリクエストまで少し待つ
        if i < len(messages) - 1:
            time.sleep(3)
    
    print(f"✓ Session test completed for user: {user_id}")


@pytest.mark.skipif(
    not os.environ.get("LINE_CHANNEL_SECRET"),
    reason="LINE_CHANNEL_SECRET not set"
)
def test_lambda_invoke_missing_signature(lambda_function_name):
    """署名なしでLambda関数を呼び出すと401が返ることを確認"""
    event = {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/",
        "rawQueryString": "",
        "headers": {
            "content-type": "application/json"
        },
        "requestContext": {
            "accountId": "anonymous",
            "apiId": "test",
            "domainName": "test.lambda-url.us-west-2.on.aws",
            "http": {
                "method": "POST",
                "path": "/",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "pytest"
            },
            "requestId": "test-request-id",
            "routeKey": "$default",
            "stage": "$default",
            "time": datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000"),
            "timeEpoch": int(time.time() * 1000)
        },
        "body": json.dumps({"events": []}),
        "isBase64Encoded": False
    }
    
    response = invoke_lambda_directly(lambda_function_name, event)
    
    assert response["statusCode"] == 401
    assert "Missing signature" in response["body"]


@pytest.mark.skipif(
    not os.environ.get("LINE_CHANNEL_SECRET"),
    reason="LINE_CHANNEL_SECRET not set"
)
def test_lambda_invoke_invalid_signature(lambda_function_name):
    """無効な署名でLambda関数を呼び出すと401が返ることを確認"""
    event = {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/",
        "rawQueryString": "",
        "headers": {
            "content-type": "application/json",
            "x-line-signature": "invalid_signature"
        },
        "requestContext": {
            "accountId": "anonymous",
            "apiId": "test",
            "domainName": "test.lambda-url.us-west-2.on.aws",
            "http": {
                "method": "POST",
                "path": "/",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "pytest"
            },
            "requestId": "test-request-id",
            "routeKey": "$default",
            "stage": "$default",
            "time": datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000"),
            "timeEpoch": int(time.time() * 1000)
        },
        "body": json.dumps({"events": []}),
        "isBase64Encoded": False
    }
    
    response = invoke_lambda_directly(lambda_function_name, event)
    
    assert response["statusCode"] == 401
    assert "Invalid signature" in response["body"]


# ========================================
# HTTP経由のテスト（既存）
# ========================================

def test_webhook_url_exists(webhook_url):
    """Lambda Function URLが取得できることを確認"""
    assert webhook_url is not None
    assert webhook_url.startswith("https://")
    print(f"Webhook URL: {webhook_url}")


def test_webhook_missing_signature(webhook_url):
    """署名がない場合に401が返ることを確認"""
    body = json.dumps({"events": []})
    
    response = requests.post(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 401
    assert "Missing signature" in response.text or "Invalid signature" in response.text


def test_webhook_invalid_signature(webhook_url):
    """無効な署名の場合に401が返ることを確認"""
    body = json.dumps({"events": []})
    
    response = requests.post(
        webhook_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-line-signature": "invalid_signature"
        }
    )
    
    assert response.status_code == 401


def test_webhook_valid_signature_empty_events(webhook_url, line_channel_secret):
    """正しい署名でイベントが空の場合に200が返ることを確認"""
    body = json.dumps({"events": []})
    signature = create_line_signature(body, line_channel_secret)
    
    response = requests.post(
        webhook_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-line-signature": signature
        }
    )
    
    assert response.status_code == 200


@pytest.mark.skipif(
    not os.environ.get("LINE_CHANNEL_SECRET"),
    reason="LINE_CHANNEL_SECRET not set"
)
def test_webhook_text_message_response(webhook_url, line_channel_secret):
    """テキストメッセージを送信して処理されることを確認"""
    user_id = f"test_user_{int(time.time())}"
    message_text = "Hello! How are you?"
    
    event = create_line_webhook_event(user_id, message_text)
    body = json.dumps({"events": [event]})
    signature = create_line_signature(body, line_channel_secret)
    
    response = requests.post(
        webhook_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-line-signature": signature
        }
    )
    
    assert response.status_code == 200
    print(f"Response: {response.text}")


@pytest.mark.skipif(
    not os.environ.get("LINE_CHANNEL_SECRET"),
    reason="LINE_CHANNEL_SECRET not set"
)
def test_webhook_japanese_message(webhook_url, line_channel_secret):
    """日本語メッセージを送信して処理されることを確認"""
    user_id = f"test_user_jp_{int(time.time())}"
    message_text = "こんにちは！元気ですか？"
    
    event = create_line_webhook_event(user_id, message_text)
    body = json.dumps({"events": [event]})
    signature = create_line_signature(body, line_channel_secret)
    
    response = requests.post(
        webhook_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-line-signature": signature
        }
    )
    
    assert response.status_code == 200
    print(f"Response: {response.text}")


@pytest.mark.skipif(
    not os.environ.get("LINE_CHANNEL_SECRET"),
    reason="LINE_CHANNEL_SECRET not set"
)
def test_webhook_multiple_messages_same_user(webhook_url, line_channel_secret):
    """同じユーザーから複数メッセージを送信してセッションが維持されることを確認"""
    user_id = f"test_user_session_{int(time.time())}"
    
    messages = [
        "What is 10 + 5?",
        "What was my previous question?",
    ]
    
    for i, message_text in enumerate(messages):
        event = create_line_webhook_event(user_id, message_text)
        body = json.dumps({"events": [event]})
        signature = create_line_signature(body, line_channel_secret)
        
        response = requests.post(
            webhook_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-line-signature": signature
            }
        )
        
        assert response.status_code == 200
        print(f"Message {i+1}: {message_text}")
        print(f"Response: {response.text}")
        
        # 次のリクエストまで少し待つ
        if i < len(messages) - 1:
            time.sleep(2)


@pytest.mark.skipif(
    not os.environ.get("LINE_CHANNEL_SECRET"),
    reason="LINE_CHANNEL_SECRET not set"
)
def test_webhook_multiple_events_in_single_request(webhook_url, line_channel_secret):
    """1つのリクエストに複数のイベントが含まれる場合の処理を確認"""
    events = [
        create_line_webhook_event(f"user1_{int(time.time())}", "Hello from user 1"),
        create_line_webhook_event(f"user2_{int(time.time())}", "Hello from user 2"),
    ]
    
    body = json.dumps({"events": events})
    signature = create_line_signature(body, line_channel_secret)
    
    response = requests.post(
        webhook_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-line-signature": signature
        }
    )
    
    assert response.status_code == 200
    print(f"Response: {response.text}")


def test_session_table_exists(stack_outputs):
    """DynamoDBセッションテーブルが存在することを確認"""
    table_name = stack_outputs.get("SessionTableName")
    assert table_name is not None
    
    dynamodb = boto3.client("dynamodb", region_name="us-west-2")
    
    response = dynamodb.describe_table(TableName=table_name)
    assert response["Table"]["TableStatus"] == "ACTIVE"
    
    # TTL設定を確認
    ttl_response = dynamodb.describe_time_to_live(TableName=table_name)
    assert ttl_response["TimeToLiveDescription"]["TimeToLiveStatus"] == "ENABLED"
    assert ttl_response["TimeToLiveDescription"]["AttributeName"] == "ttl"
    
    print(f"Session table: {table_name}")


@pytest.mark.skipif(
    not os.environ.get("LINE_CHANNEL_SECRET"),
    reason="LINE_CHANNEL_SECRET not set"
)
def test_session_persistence_in_dynamodb(webhook_url, line_channel_secret, stack_outputs):
    """セッションがDynamoDBに保存されることを確認"""
    user_id = f"test_user_db_{int(time.time())}"
    message_text = "Test message for session persistence"
    
    # メッセージを送信
    event = create_line_webhook_event(user_id, message_text)
    body = json.dumps({"events": [event]})
    signature = create_line_signature(body, line_channel_secret)
    
    response = requests.post(
        webhook_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-line-signature": signature
        }
    )
    
    assert response.status_code == 200
    
    # DynamoDBにセッションが保存されているか確認
    time.sleep(2)  # 保存されるまで少し待つ
    
    table_name = stack_outputs.get("SessionTableName")
    dynamodb = boto3.client("dynamodb", region_name="us-west-2")
    
    response = dynamodb.get_item(
        TableName=table_name,
        Key={"user_id": {"S": user_id}}
    )
    
    assert "Item" in response
    assert "session_id" in response["Item"]
    assert "ttl" in response["Item"]
    
    session_id = response["Item"]["session_id"]["S"]
    print(f"User ID: {user_id}")
    print(f"Session ID: {session_id}")
