"""
LINE Bot Lambda Function for AgentCore Runtime

LINEからのWebhookを受信し、AgentCore Runtimeのエージェントと会話する
"""
import json
import os
import hashlib
import hmac
import base64
from typing import Any, Dict
import boto3
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent


# 環境変数
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
AGENT_RUNTIME_ARN = os.environ["AGENT_RUNTIME_ARN"]
SESSION_TABLE_NAME = os.environ.get("SESSION_TABLE_NAME", "LineAgentSessions")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-west-2")

# LINE Bot SDK設定
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# AWSクライアント
bedrock_client = boto3.client("bedrock-agentcore", region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
session_table = dynamodb.Table(SESSION_TABLE_NAME)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda関数のエントリーポイント"""
    
    # Lambda Function URLからのリクエスト処理
    try:
        # 署名検証
        signature = event["headers"].get("x-line-signature", "")
        body = event.get("body", "")
        
        if not signature:
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Missing signature"})
            }
        
        # 署名検証
        if not verify_signature(body, signature):
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Invalid signature"})
            }
        
        # Webhookイベント処理
        webhook_body = json.loads(body)
        
        for webhook_event in webhook_body.get("events", []):
            handle_event(webhook_event)
        
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "OK"})
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


def verify_signature(body: str, signature: str) -> bool:
    """LINE署名を検証"""
    hash_value = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256
    ).digest()
    expected_signature = base64.b64encode(hash_value).decode("utf-8")
    return hmac.compare_digest(signature, expected_signature)


def handle_event(event: Dict[str, Any]) -> None:
    """Webhookイベントを処理"""
    
    # メッセージイベントのみ処理
    if event["type"] != "message" or event["message"]["type"] != "text":
        return
    
    user_id = event["source"]["userId"]
    reply_token = event["replyToken"]
    user_message = event["message"]["text"]
    
    print(f"Received message from {user_id}: {user_message}")
    
    # セッションIDを取得または作成
    session_id = get_or_create_session(user_id)
    
    # AgentCore Runtimeを呼び出し
    agent_response = invoke_agent(session_id, user_message)
    
    # LINE Reply APIで応答
    reply_message(reply_token, agent_response)


def get_or_create_session(user_id: str) -> str:
    """DynamoDBからセッションIDを取得、なければ新規作成"""
    
    try:
        # 既存セッションを取得
        response = session_table.get_item(Key={"user_id": user_id})
        
        if "Item" in response:
            session_id = response["Item"]["session_id"]
            print(f"Using existing session: {session_id}")
            
            # TTLを更新（24時間後）
            import time
            ttl = int(time.time()) + 86400  # 24時間
            session_table.update_item(
                Key={"user_id": user_id},
                UpdateExpression="SET #ttl = :ttl",
                ExpressionAttributeNames={"#ttl": "ttl"},
                ExpressionAttributeValues={":ttl": ttl}
            )
            
            return session_id
        
        # 新規セッション作成
        import uuid
        session_id = str(uuid.uuid4())
        
        import time
        ttl = int(time.time()) + 86400  # 24時間
        
        session_table.put_item(
            Item={
                "user_id": user_id,
                "session_id": session_id,
                "ttl": ttl
            }
        )
        
        print(f"Created new session: {session_id}")
        return session_id
        
    except Exception as e:
        print(f"Error managing session: {str(e)}")
        # エラー時は一時的なセッションIDを使用
        import uuid
        return str(uuid.uuid4())


def invoke_agent(session_id: str, user_message: str) -> str:
    """AgentCore Runtimeを呼び出し"""
    
    try:
        payload = {"prompt": user_message}
        
        response = bedrock_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_RUNTIME_ARN,
            payload=json.dumps(payload).encode("utf-8"),
            sessionId=session_id
        )
        
        # レスポンスを解析
        result = json.loads(response["response"].read())
        
        # テキスト応答を抽出
        if "result" in result and "content" in result["result"]:
            content = result["result"]["content"]
            if isinstance(content, list) and len(content) > 0:
                return content[0].get("text", "応答を取得できませんでした")
        
        return "応答を取得できませんでした"
        
    except Exception as e:
        print(f"Error invoking agent: {str(e)}")
        return f"エラーが発生しました: {str(e)}"


def reply_message(reply_token: str, message_text: str) -> None:
    """LINE Reply APIでメッセージを返信"""
    
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=message_text)]
                )
            )
        print(f"Replied: {message_text}")
        
    except Exception as e:
        print(f"Error replying message: {str(e)}")
