"""
LINE Bot Lambda Function の統合テスト

デプロイされたLambda Function URLに対してLINE Webhookリクエストを送信し、
正しく応答が返ってくることを確認する
"""
import json
import os
import hashlib
import hmac
import base64
import time
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
