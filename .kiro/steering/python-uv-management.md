---
title: Python UV Package Management
inclusion: auto
---

# Python UV Package Management Rule

このプロジェクトでは、Pythonの依存関係管理とタスク実行に `uv` を使用します。

## 基本ルール

1. **依存関係管理**: `pip` の代わりに `uv` を使用する
2. **仮想環境**: `uv venv` で作成
3. **パッケージインストール**: `uv sync` で pyproject.toml から同期
4. **スクリプト実行**: `uv run <command>` でコマンド実行

## 使用例

```bash
# 仮想環境作成
uv venv

# 依存関係のインストール
uv sync

# CDKコマンド実行
uv run cdk synth
uv run cdk deploy

# Pythonスクリプト実行
uv run python my_script.py
```

## 禁止事項

- `pip install` の使用（`uv add` または pyproject.toml に直接追加）
- `python -m venv` の使用（`uv venv` を使用）
- 仮想環境を有効化してからのコマンド実行（`uv run` を使用）

## pyproject.toml

依存関係は `pyproject.toml` の `dependencies` セクションで管理します。

```toml
[project]
dependencies = [
    "aws-cdk-lib>=2.235.1",
    "constructs>=10.0.0",
]
```
