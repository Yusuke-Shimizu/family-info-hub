#!/bin/bash
set -e

# Lambda環境変数を更新するスクリプト
# 使い方: ./scripts/update-lambda-env.sh

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Lambda環境変数更新スクリプト ===${NC}"

# 環境変数のチェック
if [ -z "$LINE_CHANNEL_ID" ]; then
    echo -e "${RED}エラー: LINE_CHANNEL_ID が設定されていません${NC}"
    echo "direnv allow を実行して .envrc を読み込んでください"
    exit 1
fi

if [ -z "$LINE_CHANNEL_SECRET" ]; then
    echo -e "${RED}エラー: LINE_CHANNEL_SECRET が設定されていません${NC}"
    echo "direnv allow を実行して .envrc を読み込んでください"
    exit 1
fi

if [ -z "$LINE_CHANNEL_ACCESS_TOKEN" ]; then
    echo -e "${RED}エラー: LINE_CHANNEL_ACCESS_TOKEN が設定されていません${NC}"
    echo "direnv allow を実行して .envrc を読み込んでください"
    exit 1
fi

# CloudFormationスタックから出力を取得
echo -e "${YELLOW}CloudFormationスタックから情報を取得中...${NC}"
STACK_NAME="CdkAgentcoreStack"
REGION="${AWS_REGION:-us-west-2}"

# Lambda関数名を取得
FUNCTION_NAME=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`LineBotWebhookUrl`].OutputValue' \
    --output text 2>/dev/null)

if [ -z "$FUNCTION_NAME" ]; then
    echo -e "${RED}エラー: スタック情報の取得に失敗しました${NC}"
    exit 1
fi

# Lambda関数名を直接取得
FUNCTION_NAME=$(aws lambda list-functions \
    --region "$REGION" \
    --query "Functions[?starts_with(FunctionName, 'CdkAgentcoreStack-LineBotWebhookHandler')].FunctionName" \
    --output text)

if [ -z "$FUNCTION_NAME" ]; then
    echo -e "${RED}エラー: Lambda関数が見つかりません${NC}"
    exit 1
fi

echo -e "${GREEN}Lambda関数: $FUNCTION_NAME${NC}"

# AgentCore RuntimeのARNを取得
AGENT_RUNTIME_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`AgentRuntimeArn`].OutputValue' \
    --output text)

# DynamoDBテーブル名を取得
SESSION_TABLE_NAME=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`SessionTableName`].OutputValue' \
    --output text)

echo -e "${YELLOW}環境変数を更新中...${NC}"

# Lambda環境変数を更新
aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION" \
    --environment "Variables={
        LINE_CHANNEL_ID=$LINE_CHANNEL_ID,
        LINE_CHANNEL_ACCESS_TOKEN=$LINE_CHANNEL_ACCESS_TOKEN,
        LINE_CHANNEL_SECRET=$LINE_CHANNEL_SECRET,
        AGENT_RUNTIME_ARN=$AGENT_RUNTIME_ARN,
        SESSION_TABLE_NAME=$SESSION_TABLE_NAME
    }" \
    --output json > /dev/null

echo -e "${GREEN}✓ 環境変数の更新が完了しました${NC}"

# 設定内容を確認（トークンは一部マスク）
echo ""
echo -e "${YELLOW}設定内容:${NC}"
echo "  LINE_CHANNEL_ID: $LINE_CHANNEL_ID"
echo "  LINE_CHANNEL_ACCESS_TOKEN: ${LINE_CHANNEL_ACCESS_TOKEN:0:20}...（マスク）"
echo "  LINE_CHANNEL_SECRET: ${LINE_CHANNEL_SECRET:0:10}...（マスク）"
echo "  AGENT_RUNTIME_ARN: $AGENT_RUNTIME_ARN"
echo "  SESSION_TABLE_NAME: $SESSION_TABLE_NAME"
echo ""
echo -e "${GREEN}Lambda関数の準備が完了しました！${NC}"
echo "次のステップ:"
echo "  1. LINE Developers ConsoleでWebhook URLを設定"
echo "  2. Botを友だち追加してテスト"
