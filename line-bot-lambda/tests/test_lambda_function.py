"""
LINE Bot Lambda Function のテスト
"""
import json
import os
import hashlib
import hmac
import base64
from unittest.mock import Mock, patch, MagicMock
import pytest
from moto import mock_aws
import boto3


# 環境変数を設定
os.environ["LINE_CHANNEL_ACCESS_TOKEN"] = "test_access_token"
os.environ["LINE_CHANNEL_SECRET"] = "test_channel_secret"
os.environ["AGENT_RUNTIME_ARN"] = "arn:aws:bedrock-agentcore:us-west-2:000000000000:runtime/test-agent"
os.environ["SESSION_TABLE_NAME"] = "TestLineAgentSessions"

# テスト用にモジュールをインポート
import lambda_function


@pytest.fixture
def mock_dynamodb():
    """DynamoDBのモック"""
    with mock_aws():
        # DynamoDBテーブルを作成
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
        table = dynamodb.create_table(
            TableName="TestLineAgentSessions",
            KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table


@pytest.fixture
def line_webhook_event():
    """LINE Webhookイベントのサンプル"""
    return {
        "type": "message",
        "replyToken": "test_reply_token",
        "source": {"userId": "test_user_id"},
        "message": {"type": "text", "text": "こんにちは"},
    }


@pytest.fixture
def lambda_event(line_webhook_event):
    """Lambda Function URLからのイベント"""
    body = json.dumps({"events": [line_webhook_event]})
    
    # 署名を生成
    signature = create_signature(body)
    
    return {
        "headers": {"x-line-signature": signature},
        "body": body,
    }


def create_signature(body: str) -> str:
    """LINE署名を生成"""
    hash_value = hmac.new(
        os.environ["LINE_CHANNEL_SECRET"].encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(hash_value).decode("utf-8")


def test_verify_signature_valid():
    """署名検証が正しく動作することを確認"""
    body = "test body"
    signature = create_signature(body)
    
    assert lambda_function.verify_signature(body, signature) is True


def test_verify_signature_invalid():
    """無効な署名が拒否されることを確認"""
    body = "test body"
    invalid_signature = "invalid_signature"
    
    assert lambda_function.verify_signature(body, invalid_signature) is False


def test_lambda_handler_missing_signature():
    """署名がない場合に401を返すことを確認"""
    event = {"headers": {}, "body": "{}"}
    
    response = lambda_function.lambda_handler(event, None)
    
    assert response["statusCode"] == 401
    assert "Missing signature" in response["body"]


def test_lambda_handler_invalid_signature():
    """無効な署名の場合に401を返すことを確認"""
    event = {
        "headers": {"x-line-signature": "invalid"},
        "body": json.dumps({"events": []}),
    }
    
    response = lambda_function.lambda_handler(event, None)
    
    assert response["statusCode"] == 401
    assert "Invalid signature" in response["body"]


@patch("lambda_function.handle_event")
def test_lambda_handler_success(mock_handle_event, lambda_event):
    """正常なリクエストが処理されることを確認"""
    mock_handle_event.return_value = None
    
    response = lambda_function.lambda_handler(lambda_event, None)
    
    assert response["statusCode"] == 200
    assert mock_handle_event.called


def test_get_or_create_session_new(mock_dynamodb):
    """新規セッションが作成されることを確認"""
    user_id = "new_user"
    
    session_id = lambda_function.get_or_create_session(user_id)
    
    # セッションIDが生成されていることを確認
    assert session_id is not None
    assert len(session_id) > 0
    
    # DynamoDBに保存されていることを確認
    response = mock_dynamodb.get_item(Key={"user_id": user_id})
    assert "Item" in response
    assert response["Item"]["session_id"] == session_id


def test_get_or_create_session_existing(mock_dynamodb):
    """既存セッションが取得されることを確認"""
    user_id = "existing_user"
    existing_session_id = "existing_session_123"
    
    # 既存セッションを作成
    import time
    mock_dynamodb.put_item(
        Item={
            "user_id": user_id,
            "session_id": existing_session_id,
            "ttl": int(time.time()) + 86400,
        }
    )
    
    session_id = lambda_function.get_or_create_session(user_id)
    
    # 既存のセッションIDが返されることを確認
    assert session_id == existing_session_id


@patch("lambda_function.bedrock_client")
def test_invoke_agent_success(mock_bedrock_client):
    """AgentCore Runtimeの呼び出しが成功することを確認"""
    # モックレスポンスを設定
    mock_response_body = MagicMock()
    mock_response_body.read.return_value = json.dumps({
        "result": {
            "content": [{"text": "こんにちは！元気ですよ。"}]
        }
    }).encode("utf-8")
    
    mock_bedrock_client.invoke_agent_runtime.return_value = {
        "response": mock_response_body
    }
    
    response = lambda_function.invoke_agent("test_session", "こんにちは")
    
    assert response == "こんにちは！元気ですよ。"
    assert mock_bedrock_client.invoke_agent_runtime.called


@patch("lambda_function.bedrock_client")
def test_invoke_agent_error(mock_bedrock_client):
    """AgentCore Runtimeのエラーが処理されることを確認"""
    mock_bedrock_client.invoke_agent_runtime.side_effect = Exception("Test error")
    
    response = lambda_function.invoke_agent("test_session", "こんにちは")
    
    assert "エラーが発生しました" in response


@patch("lambda_function.MessagingApi")
def test_reply_message_success(mock_messaging_api):
    """LINE Reply APIが正しく呼び出されることを確認"""
    mock_api_instance = MagicMock()
    mock_messaging_api.return_value = mock_api_instance
    
    lambda_function.reply_message("test_reply_token", "テストメッセージ")
    
    assert mock_api_instance.reply_message.called


@patch("lambda_function.get_or_create_session")
@patch("lambda_function.invoke_agent")
@patch("lambda_function.reply_message")
def test_handle_event_text_message(
    mock_reply, mock_invoke, mock_get_session, line_webhook_event
):
    """テキストメッセージイベントが正しく処理されることを確認"""
    mock_get_session.return_value = "test_session_id"
    mock_invoke.return_value = "エージェントの応答"
    
    lambda_function.handle_event(line_webhook_event)
    
    # セッション取得が呼ばれたことを確認
    mock_get_session.assert_called_once_with("test_user_id")
    
    # エージェント呼び出しが呼ばれたことを確認
    mock_invoke.assert_called_once_with("test_session_id", "こんにちは")
    
    # 返信が呼ばれたことを確認
    mock_reply.assert_called_once_with("test_reply_token", "エージェントの応答")


def test_handle_event_non_text_message():
    """テキスト以外のメッセージが無視されることを確認"""
    event = {
        "type": "message",
        "message": {"type": "image"},
    }
    
    # エラーが発生しないことを確認
    lambda_function.handle_event(event)


def test_handle_event_non_message_event():
    """メッセージ以外のイベントが無視されることを確認"""
    event = {
        "type": "follow",
        "source": {"userId": "test_user"},
    }
    
    # エラーが発生しないことを確認
    lambda_function.handle_event(event)


@patch("lambda_function.handle_event")
def test_lambda_handler_multiple_events(mock_handle_event):
    """複数のイベントが処理されることを確認"""
    events = [
        {
            "type": "message",
            "message": {"type": "text", "text": "メッセージ1"},
            "source": {"userId": "user1"},
            "replyToken": "token1",
        },
        {
            "type": "message",
            "message": {"type": "text", "text": "メッセージ2"},
            "source": {"userId": "user2"},
            "replyToken": "token2",
        },
    ]
    
    body = json.dumps({"events": events})
    signature = create_signature(body)
    
    event = {
        "headers": {"x-line-signature": signature},
        "body": body,
    }
    
    response = lambda_function.lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    assert mock_handle_event.call_count == 2
