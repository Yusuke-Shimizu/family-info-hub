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
    MessagingApiBlob,
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
MEMORY_ID = os.environ.get("MEMORY_ID", "")

# LINE Bot SDK設定
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# AWSクライアント
bedrock_client = boto3.client("bedrock-agentcore", region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
session_table = dynamodb.Table(SESSION_TABLE_NAME)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda関数のエントリーポイント"""
    
    print(f"Received event: {json.dumps(event)}")
    
    # Lambda Function URLからのリクエスト処理
    try:
        # 署名検証
        signature = event["headers"].get("x-line-signature", "")
        body = event.get("body", "")
        
        print(f"Signature present: {bool(signature)}")
        print(f"Body length: {len(body)}")
        
        if not signature:
            print("Missing signature")
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Missing signature"})
            }
        
        # 署名検証
        if not verify_signature(body, signature):
            print("Invalid signature")
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Invalid signature"})
            }
        
        print("Signature verified successfully")
        
        # Webhookイベント処理
        webhook_body = json.loads(body)
        events = webhook_body.get("events", [])
        print(f"Processing {len(events)} events")
        
        for webhook_event in events:
            print(f"Event type: {webhook_event.get('type')}")
            handle_event(webhook_event)
        
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "OK"})
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
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


def get_session_key(event: Dict[str, Any]) -> str:
    """会話のコンテキストに応じたセッションキーを返す"""
    source = event["source"]
    source_type = source["type"]

    if source_type == "group":
        return source["groupId"]
    elif source_type == "room":
        return source["roomId"]
    else:
        return source["userId"]


def handle_event(event: Dict[str, Any]) -> None:
    """Webhookイベントを処理"""

    if event["type"] != "message":
        return

    message_type = event["message"]["type"]
    user_id = event["source"].get("userId", "unknown")
    session_key = get_session_key(event)
    reply_token = event["replyToken"]

    print(f"source_type={event['source']['type']}, session_key={session_key}, user_id={user_id}")

    if message_type == "text":
        user_message = event["message"]["text"]
        print(f"Received text message: {user_message}")

        session_id = get_or_create_session(session_key)

        # 短期記憶（現セッションの会話履歴）を取得
        short_term_context = get_short_term_memory(session_key, session_id)

        # 長期記憶（過去セッションの知識）をセマンティック検索
        long_term_context = get_long_term_memory(session_key, user_message)

        agent_response = invoke_agent(session_id, user_message, short_term_context, long_term_context)

        # 会話を短期記憶に記録
        save_conversation(session_key, session_id, user_message, agent_response)

        reply_message(reply_token, agent_response)

    elif message_type == "image":
        message_id = event["message"]["id"]
        print(f"Received image message, message_id: {message_id}")

        image_response = analyze_image(message_id)
        session_id = get_or_create_session(session_key)

        # 画像分析結果も短期記憶に記録
        save_conversation(session_key, session_id, "[画像を送信]", image_response)

        reply_message(reply_token, image_response)

    else:
        print(f"Unsupported message type: {message_type}")


def analyze_image(message_id: str) -> str:
    """LINE画像をダウンロードしてClaude visionで分析"""

    try:
        # LINE APIから画像をダウンロード
        with ApiClient(configuration) as api_client:
            blob_api = MessagingApiBlob(api_client)
            image_content = blob_api.get_message_content(message_id=message_id)

        image_base64 = base64.b64encode(image_content).decode("utf-8")
        print(f"Downloaded image, size: {len(image_content)} bytes")

        # Bedrock Claude visionで分析
        bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": "この画像について日本語で説明してください。",
                        },
                    ],
                }
            ],
        }

        response = bedrock_runtime.invoke_model(
            modelId="us.anthropic.claude-sonnet-4-6",
            body=json.dumps(body),
        )
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]

    except Exception as e:
        print(f"Error analyzing image: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return f"画像の分析中にエラーが発生しました: {str(e)}"


def get_short_term_memory(actor_id: str, session_id: str) -> str:
    """短期記憶（Events）から現セッションの会話履歴を取得"""
    if not MEMORY_ID:
        return ""
    try:
        resp = bedrock_client.list_events(
            memoryId=MEMORY_ID,
            actorId=actor_id,
            sessionId=session_id,
            maxResults=10,
        )
        lines = []
        for ev in resp.get("events", []):
            for item in ev.get("payload", []):
                conv = item.get("conversational", {})
                role = conv.get("role", "USER")
                text = conv.get("content", {}).get("text", "")
                if text:
                    lines.append(f"{role}: {text}")
        print(f"Short-term memory: {len(lines)} turns retrieved")
        return "\n".join(lines)
    except Exception as e:
        print(f"list_events error: {e}")
        return ""


def get_long_term_memory(actor_id: str, query: str) -> str:
    """長期記憶から関連情報をセマンティック検索"""
    if not MEMORY_ID:
        return ""
    namespaces = [
        f"/family/{actor_id}/facts/",
        f"/family/{actor_id}/preferences/",
    ]
    results = []
    for ns in namespaces:
        try:
            resp = bedrock_client.retrieve_memory_records(
                memoryId=MEMORY_ID,
                namespace=ns,
                searchCriteria={"searchQuery": query, "topK": 3}
            )
            for r in resp.get("memoryRecordSummaries", []):
                results.append(r["content"]["text"])
        except Exception as e:
            print(f"retrieve_memory_records error ({ns}): {e}")
    return "\n".join(results)


def save_conversation(actor_id: str, session_id: str, user_msg: str, assistant_msg: str) -> None:
    """会話をAgentCore Memoryの短期記憶（Events）に記録"""
    if not MEMORY_ID:
        return
    from datetime import datetime, timezone
    try:
        bedrock_client.create_event(
            memoryId=MEMORY_ID,
            actorId=actor_id,
            sessionId=session_id,
            eventTimestamp=datetime.now(timezone.utc),
            payload=[
                {"conversational": {"content": {"text": user_msg}, "role": "USER"}},
                {"conversational": {"content": {"text": assistant_msg}, "role": "ASSISTANT"}},
            ]
        )
        print(f"Saved conversation event for actor={actor_id}, session={session_id}")
    except Exception as e:
        print(f"create_event error: {e}")


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


def invoke_agent(session_id: str, user_message: str, short_term_context: str = "", long_term_context: str = "") -> str:
    """AgentCore Runtimeを呼び出し"""

    try:
        sections = []
        if long_term_context:
            sections.append(f"[過去の長期記憶]\n{long_term_context}")
        if short_term_context:
            sections.append(f"[今セッションの会話履歴]\n{short_term_context}")
        sections.append(f"[ユーザーのメッセージ]\n{user_message}")
        prompt = "\n\n".join(sections)
        payload = {"prompt": prompt}
        
        response = bedrock_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_RUNTIME_ARN,
            payload=json.dumps(payload).encode("utf-8"),
            runtimeSessionId=session_id
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
