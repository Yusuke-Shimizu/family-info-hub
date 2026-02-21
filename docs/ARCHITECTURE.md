# システム設計図

## 目次
1. [現在のアーキテクチャ（As-Is）](#現在のアーキテクチャas-is)
2. [将来のアーキテクチャ（To-Be）](#将来のアーキテクチャto-be)
3. [メモリ設計](#メモリ設計)

---

## 現在のアーキテクチャ（As-Is）

### 構成図

```
┌─────────────────────────────────────────────────────────────────┐
│ LINEアプリ                                                       │
│                                                                  │
│  個人チャット ──┐                                                │
│  グループ    ──┤  Webhook（HTTP POST）                           │
│  複数人    ──┘                                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Lambda Function URL                                              │
│  https://vrtk62lq...lambda-url.us-west-2.on.aws/               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Lambda（LINE Bot Webhook Handler）                               │
│                                                                  │
│  1. LINE署名検証（HMAC-SHA256）                                  │
│  2. メッセージタイプの判定                                        │
│     ├── text  → AgentCore Runtime 呼び出し                       │
│     ├── image → Bedrock Claude Vision 分析                       │
│     └── other → スキップ                                         │
│  3. セッションキー取得（get_session_key）                         │
│     ├── source.type = "group" → groupId                         │
│     ├── source.type = "room"  → roomId                          │
│     └── source.type = "user"  → userId                          │
│  4. LINE Reply APIで返信                                         │
└───────┬──────────────────────────┬──────────────────────────────┘
        │                          │
        ▼                          ▼
┌───────────────┐      ┌───────────────────────────────────────────┐
│ DynamoDB      │      │ AgentCore Runtime (my_agent)              │
│ LineAgent     │      │                                           │
│ Sessions      │      │  Strands Agent（Claudeモデル）            │
│               │      │  ├── 短期コンテキスト: runtimeSessionId  │
│ session_key   │      │  │   （最大15分 / アイドルタイムアウト）  │
│ → session_id  │      │  └── 長期記憶: なし ❌                   │
│ (TTL: 24h)    │      │                                           │
└───────────────┘      └───────────────────┬───────────────────────┘
                                           │
                                           ▼
                             ┌─────────────────────────┐
                             │ Amazon Bedrock           │
                             │ Claude（モデル）         │
                             └─────────────────────────┘
```

### 現状の問題点

| 問題 | 詳細 |
|------|------|
| **短期記憶の揮発性** | AgentCore RuntimeのアイドルタイムアウトはHIが900秒（15分）。それ以降は会話コンテキストが消える |
| **長期記憶がない** | セッションをまたいだ記憶保持ができない（「以前話したこと」を覚えていない） |
| **DynamoDBはID管理のみ** | session_key → session_id のマッピングのみ。会話内容は保存していない |
| **画像はメモリに残らない** | 画像分析結果はそのターンで消える |

---

## 将来のアーキテクチャ（To-Be）

### 構成図

```
┌─────────────────────────────────────────────────────────────────┐
│ LINEアプリ                                                       │
│  個人チャット / グループ / 複数人                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Webhook
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Lambda（LINE Bot Webhook Handler）                               │
│                                                                  │
│  1. LINE署名検証                                                 │
│  2. メッセージタイプ判定（text / image）                          │
│  3. session_key 決定（groupId / userId）                         │
│  4. AgentCore Memory から長期記憶を検索・取得 ◀── NEW            │
│  5. AgentCore Runtime 呼び出し（記憶をコンテキストに付加）        │
│  6. 会話をAgentCore Memory に記録（短期記憶）◀── NEW             │
│  7. LINE Reply APIで返信                                         │
└───────┬──────────────────────────┬──────────────────────────────┘
        │                          │
        ▼                          ▼
┌───────────────┐      ┌───────────────────────────────────────────┐
│ DynamoDB      │      │ AgentCore Runtime (my_agent)              │
│ LineAgent     │      │  Strands Agent（Claudeモデル）            │
│ Sessions      │      │  ＋ AgentCore Memory 統合                 │
│               │      └───────────────────┬───────────────────────┘
│ session_key   │                          │
│ → session_id  │      ┌───────────────────▼───────────────────────┐
│ (TTL: 24h)    │      │ AgentCore Memory（family-info-hub用）NEW   │
└───────────────┘      │                                           │
                       │  ┌── 短期記憶（Events）                   │
                       │  │   会話ターンを記録                      │
                       │  │   有効期限: 90日                        │
                       │  │   actorId = session_key               │
                       │  │                                        │
                       │  └── 長期記憶（Memory Records）           │
                       │      重要情報を自動抽出・永続保存          │
                       │      戦略1: SEMANTIC（家族の基本情報）     │
                       │      戦略2: USER_PREFERENCE（好み・設定） │
                       │      戦略3: EPISODIC（出来事・イベント）   │
                       │      namespace: /family/{actorId}        │
                       └───────────────────────────────────────────┘
```

---

## メモリ設計

### 識別子の対応関係

```
LINEの会話コンテキスト          AgentCore Memoryの識別子
─────────────────────          ─────────────────────────
グループチャット(groupId)   →   actorId = groupId
個人チャット(userId)        →   actorId = userId
会話セッション(UUID)        →   sessionId = session_id（DynamoDB管理）
```

### 短期記憶（Events）

- **用途**: 同一セッション内の会話履歴を保持
- **有効期限**: 90日
- **効果**: AgentCore Runtimeのアイドルタイムアウトにかかわらず会話を継続できる

```
[LINEメッセージ受信]
      ↓
list_events(memoryId, sessionId, actorId) で過去の会話を取得
      ↓
AgentCore Runtime 呼び出し（会話履歴をコンテキストとして付加）
      ↓
create_event(memoryId, sessionId, actorId, payload) で記録
```

### 長期記憶（Memory Records）

- **用途**: セッションをまたいだ重要情報の保持
- **namespace**: `/family/{actorId}`
- **効果**: 「子どもの名前」「アレルギー情報」「好みの話題」「過去の出来事」などを長期保持

#### メモリ戦略

| 戦略 | namespace | 保存される内容 | 例 |
|------|-----------|--------------|-----|
| **SEMANTIC** | `/family/{actorId}/facts` | 家族の基本情報・事実 | 「子どもの名前は○○」「アレルギーはエビ」 |
| **USER_PREFERENCE** | `/family/{actorId}/preferences` | グループ・個人の好みや設定 | 「丁寧語で話してほしい」「料理の話題が多い」 |
| **EPISODIC** | `/family/{actorId}/episodes` | 過去の出来事・イベント | 「2/21に懇談会の資料を共有した」「先週の行事の決め事」 |

> **採用しない戦略**
> `SUMMARIZATION` → 短期記憶（Events）が90日保持されるため不要
> `CUSTOM` → 工数対効果が低いため当面は見送り

```
[Events が一定量蓄積]
      ↓
AgentCore が自動的に重要情報を抽出（Memory Extraction Job）
      ↓
戦略ごとに Memory Records として永続保存
      ↓
次回以降の会話で retrieve_memory_records() で検索・活用
```

### グループ vs 個人の記憶分離

```
グループA (groupId=Cxxx)
  ├── 短期記憶: グループ全体の会話履歴
  └── 長期記憶: グループとしての情報（行事予定、決定事項 等）

個人ユーザー (userId=Uyyy)
  ├── 短期記憶: 個人とBotの会話履歴
  └── 長期記憶: 個人の情報（名前、好み、家族構成 等）
```

### 実装ステップ（To-Beへの移行計画）

| ステップ | 内容 | 変更箇所 |
|---------|------|---------|
| 1 | AgentCore Memory リソース作成 | CDKスタック |
| 2 | Lambda に Memory 操作の IAM 権限追加 | CDKスタック |
| 3 | Lambda 環境変数に MEMORY_ID 追加 | CDKスタック |
| 4 | メッセージ受信時に Events を記録 | lambda_function.py |
| 5 | AgentCore 呼び出し時に会話履歴を付加 | lambda_function.py |
| 6 | 長期記憶の検索結果をコンテキストに追加 | lambda_function.py |
