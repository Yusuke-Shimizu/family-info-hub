#!/bin/bash
set -e

# LINE認証情報セットアップスクリプト
# 使い方: ./scripts/setup-line-credentials.sh

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== LINE認証情報セットアップ ===${NC}"
echo ""

# .envrcファイルの存在確認
if [ -f ".envrc" ]; then
    echo -e "${YELLOW}⚠️  .envrc ファイルが既に存在します${NC}"
    read -p "上書きしますか？ (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}既存の .envrc を使用します${NC}"
        exit 0
    fi
fi

# .envrc.exampleをコピー
echo -e "${YELLOW}1. .envrc.example から .envrc を作成中...${NC}"
cp .envrc.example .envrc
echo -e "${GREEN}✓ .envrc ファイルを作成しました${NC}"
echo ""

# 認証情報の入力
echo -e "${YELLOW}2. LINE認証情報を入力してください${NC}"
echo -e "${BLUE}LINE Developers Console (https://developers.line.biz/console/) から取得してください${NC}"
echo ""

# Channel ID
read -p "Channel ID: " CHANNEL_ID
if [ -z "$CHANNEL_ID" ]; then
    echo -e "${RED}エラー: Channel IDが入力されていません${NC}"
    exit 1
fi

# Channel Secret
read -p "Channel Secret: " CHANNEL_SECRET
if [ -z "$CHANNEL_SECRET" ]; then
    echo -e "${RED}エラー: Channel Secretが入力されていません${NC}"
    exit 1
fi

# Channel Access Token
echo "Channel Access Token (長いトークンです):"
read -p "> " CHANNEL_ACCESS_TOKEN
if [ -z "$CHANNEL_ACCESS_TOKEN" ]; then
    echo -e "${RED}エラー: Channel Access Tokenが入力されていません${NC}"
    exit 1
fi

echo ""

# .envrcファイルを更新
echo -e "${YELLOW}3. .envrc ファイルに認証情報を書き込み中...${NC}"

cat > .envrc << EOF
# LINE Messaging API 認証情報
# このファイルは .gitignore に含まれているので安全です

export LINE_CHANNEL_ID="$CHANNEL_ID"
export LINE_CHANNEL_SECRET="$CHANNEL_SECRET"
export LINE_CHANNEL_ACCESS_TOKEN="$CHANNEL_ACCESS_TOKEN"

# AWS設定
export AWS_REGION="us-west-2"
export AWS_PROFILE="default"
EOF

echo -e "${GREEN}✓ 認証情報を .envrc に保存しました${NC}"
echo ""

# direnv allow
echo -e "${YELLOW}4. direnv で環境変数を読み込み中...${NC}"
if command -v direnv &> /dev/null; then
    direnv allow
    echo -e "${GREEN}✓ 環境変数を読み込みました${NC}"
else
    echo -e "${RED}⚠️  direnv がインストールされていません${NC}"
    echo "手動で 'direnv allow' を実行してください"
fi

echo ""
echo -e "${GREEN}=== セットアップ完了 ===${NC}"
echo ""
echo -e "${BLUE}次のステップ:${NC}"
echo "  1. 環境変数が読み込まれているか確認:"
echo "     ${YELLOW}echo \$LINE_CHANNEL_ID${NC}"
echo ""
echo "  2. Lambda関数に環境変数を設定:"
echo "     ${YELLOW}./scripts/update-lambda-env.sh${NC}"
echo ""
echo "  3. LINE Developers ConsoleでWebhook URLを設定"
echo "  4. Botを友だち追加してテスト"
echo ""
echo -e "${BLUE}詳細は docs/LINE_CREDENTIALS_SETUP.md を参照してください${NC}"
