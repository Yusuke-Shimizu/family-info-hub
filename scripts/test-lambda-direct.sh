#!/bin/bash
set -e

# Lambda関数を直接呼び出してテストするスクリプト

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Lambda関数 直接テスト ===${NC}"
echo ""

# Lambda関数名を取得
FUNCTION_NAME=$(aws lambda list-functions \
  --region us-west-2 \
  --query "Functions[?starts_with(FunctionName, 'CdkAgentcoreStack-LineBotWebhookHandler')].FunctionName" \
  --output text)

if [ -z "$FUNCTION_NAME" ]; then
    echo -e "${RED}エラー: Lambda関数が見つかりません${NC}"
    exit 1
fi

echo -e "${BLUE}Lambda関数: $FUNCTION_NAME${NC}"
echo ""

# テストメッセージ
TEST_MESSAGE=${1:-"こんにちは"}
echo -e "${YELLOW}テストメッセージ: $TEST_MESSAGE${NC}"
echo ""

# LINE Webhookイベントを模擬
# 署名は正しく計算する必要があるため、実際のLINE署名を使用
BODY=$(cat <<EOF
{
  "destination": "U7ec458a9126db9a7cb49d5f2d2850d9e",
  "events": [
    {
      "type": "message",
      "message": {
        "type": "text",
        "id": "test-message-id",
        "text": "$TEST_MESSAGE"
      },
      "webhookEventId": "test-webhook-event-id",
      "deliveryContext": {
        "isRedelivery": false
      },
      "timestamp": $(date +%s)000,
      "source": {
        "type": "user",
        "userId": "test-user-id"
      },
      "replyToken": "test-reply-token",
      "mode": "active"
    }
  ]
}
EOF
)

# 署名を計算
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$LINE_CHANNEL_SECRET" -binary | base64)

# Lambda Function URLイベント形式
EVENT=$(cat <<EOF
{
  "version": "2.0",
  "routeKey": "\$default",
  "rawPath": "/",
  "rawQueryString": "",
  "headers": {
    "content-type": "application/json; charset=utf-8",
    "x-line-signature": "$SIGNATURE",
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
    "routeKey": "\$default",
    "stage": "\$default",
    "time": "$(date -u +"%d/%b/%Y:%H:%M:%S +0000")",
    "timeEpoch": $(date +%s)000
  },
  "body": $(echo "$BODY" | jq -c .),
  "isBase64Encoded": false
}
EOF
)

echo -e "${YELLOW}Lambda関数を呼び出し中...${NC}"
echo ""

# Lambda関数を呼び出し
RESPONSE=$(aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --region us-west-2 \
  --payload "$EVENT" \
  --cli-binary-format raw-in-base64-out \
  /dev/stdout 2>&1)

# レスポンスを解析
STATUS_CODE=$(echo "$RESPONSE" | jq -r '.statusCode' 2>/dev/null || echo "error")

if [ "$STATUS_CODE" = "200" ]; then
    echo -e "${GREEN}✓ 成功！${NC}"
    echo ""
    echo -e "${BLUE}レスポンス:${NC}"
    echo "$RESPONSE" | jq .
else
    echo -e "${RED}✗ エラーが発生しました${NC}"
    echo ""
    echo -e "${BLUE}レスポンス:${NC}"
    echo "$RESPONSE" | jq .
    
    # ログを確認
    echo ""
    echo -e "${YELLOW}最新のログ:${NC}"
    aws logs tail /aws/lambda/$FUNCTION_NAME \
      --region us-west-2 \
      --since 1m \
      --format short | tail -20
fi

echo ""
echo -e "${BLUE}詳細なログを確認:${NC}"
echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --region us-west-2 --since 2m"
