#!/usr/bin/env python3
"""
Lambda関数を直接呼び出してテストするスクリプト
"""
import json
import sys
import os
import hmac
import hashlib
import base64
from datetime import datetime
import boto3

# 環境変数から取得
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")

if not LINE_CHANNEL_SECRET:
    print("エラー: LINE_CHANNEL_SECRET 環境変数が設定されていません")
    print("direnv allow を実行してください")
    sys.exit(1)


def create_signature(body: str) -> str:
    """LINE署名を生成"""
    hash_value = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256
    ).digest()
    return base64.b64encode(hash_value).decode("utf-8")


def create_test_event(message: str) -> dict:
    """テスト用のLambda Function URLイベントを作成"""
    
    # LINE Webhookイベント
    webhook_body = {
        "destination": "U7ec458a9126db9a7cb49d5f2d2850d9e",
        "events": [
            {
                "type": "message",
                "message": {
                    "type": "text",
                    "id": "test-message-id",
                    "text": message
                },
                "webhookEventId": "test-webhook-event-id",
                "deliveryContext": {
                    "isRedelivery": False
                },
                "timestamp": int(datetime.now().timestamp() * 1000),
                "source": {
                    "type": "user",
                    "userId": "test-user-id"
                },
                "replyToken": "test-reply-token",
                "mode": "active"
            }
        ]
    }
    
    body = json.dumps(webhook_body)
    signature = create_signature(body)
    
    # Lambda Function URLイベント
    event = {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/",
        "rawQueryString": "",
        "headers": {
            "content-type": "application/json; charset=utf-8",
            "x-line-signature": signature,
            "user-agent": "test-script"
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
                "userAgent": "test-script"
            },
            "requestId": "test-request-id",
            "routeKey": "$default",
            "stage": "$default",
            "time": datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000"),
            "timeEpoch": int(datetime.now().timestamp() * 1000)
        },
        "body": body,
        "isBase64Encoded": False
    }
    
    return event


def invoke_lambda(function_name: str, event: dict) -> dict:
    """Lambda関数を呼び出し"""
    lambda_client = boto3.client("lambda", region_name=AWS_REGION)
    
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(event).encode("utf-8")
    )
    
    payload = json.loads(response["Payload"].read())
    return payload


def get_lambda_function_name() -> str:
    """Lambda関数名を取得"""
    lambda_client = boto3.client("lambda", region_name=AWS_REGION)
    
    response = lambda_client.list_functions()
    
    for function in response["Functions"]:
        if function["FunctionName"].startswith("CdkAgentcoreStack-LineBotWebhookHandler"):
            return function["FunctionName"]
    
    raise Exception("Lambda関数が見つかりません")


def get_recent_logs(function_name: str, minutes: int = 2):
    """最近のログを取得"""
    logs_client = boto3.client("logs", region_name=AWS_REGION)
    log_group = f"/aws/lambda/{function_name}"
    
    import time
    start_time = int((time.time() - minutes * 60) * 1000)
    
    try:
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=start_time,
            limit=50
        )
        
        return [event["message"] for event in response.get("events", [])]
    except Exception as e:
        return [f"ログ取得エラー: {str(e)}"]


def main():
    """メイン処理"""
    
    # テストメッセージ
    message = sys.argv[1] if len(sys.argv) > 1 else "こんにちは"
    
    print("=== Lambda関数 直接テスト ===")
    print()
    
    # Lambda関数名を取得
    try:
        function_name = get_lambda_function_name()
        print(f"Lambda関数: {function_name}")
    except Exception as e:
        print(f"エラー: {e}")
        sys.exit(1)
    
    print(f"テストメッセージ: {message}")
    print()
    
    # テストイベントを作成
    event = create_test_event(message)
    
    # Lambda関数を呼び出し
    print("Lambda関数を呼び出し中...")
    print()
    
    try:
        response = invoke_lambda(function_name, event)
        
        status_code = response.get("statusCode", "error")
        
        if status_code == 200:
            print("✓ 成功！")
            print()
            print("レスポンス:")
            print(json.dumps(response, indent=2, ensure_ascii=False))
        else:
            print("✗ エラーが発生しました")
            print()
            print("レスポンス:")
            print(json.dumps(response, indent=2, ensure_ascii=False))
            
            # ログを確認
            print()
            print("最新のログ:")
            logs = get_recent_logs(function_name, minutes=1)
            for log in logs[-20:]:
                print(log.rstrip())
    
    except Exception as e:
        print(f"エラー: {e}")
        
        # ログを確認
        print()
        print("最新のログ:")
        logs = get_recent_logs(function_name, minutes=1)
        for log in logs[-20:]:
            print(log.rstrip())
        
        sys.exit(1)
    
    print()
    print("詳細なログを確認:")
    print(f"  aws logs tail /aws/lambda/{function_name} --region {AWS_REGION} --since 2m")


if __name__ == "__main__":
    main()
