# Git履歴のクリーンアップガイド

## 概要

このドキュメントでは、Gitの履歴に含まれるシークレット情報（アカウントID、トークンなど）を削除する方法を説明します。

## 現状

gitleaksスキャンにより、過去のコミットに以下の情報が含まれていることが検出されています：

- AWSアカウントID
- テスト用のダミーアカウントID
- OIDCプロバイダーのサムプリント

これらは現在のコードからは削除されていますが、Git履歴に残っています。

## 対応方法

### オプション1: 履歴を書き換える（推奨しない）

⚠️ **警告**: この方法は既にプッシュされたコミットを変更するため、他の開発者に影響を与えます。

```bash
# BFG Repo-Cleanerを使用（推奨）
brew install bfg

# アカウントIDを含むファイルを削除
bfg --delete-files setup-aws-oidc.md

# または特定の文字列を置換
bfg --replace-text replacements.txt

# 履歴を書き換え
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 強制プッシュ（危険）
git push --force
```

### オプション2: 新しいリポジトリを作成（最も安全）

1. 現在のコードを新しいリポジトリにコピー
2. 履歴なしで新規コミット
3. 古いリポジトリをアーカイブ

```bash
# 新しいディレクトリを作成
mkdir family-info-hub-clean
cd family-info-hub-clean

# 現在のコードをコピー（.gitを除く）
rsync -av --exclude='.git' ../family-info-hub/ .

# 新しいGitリポジトリを初期化
git init
git add .
git commit -m "Initial commit: Clean repository without sensitive history"

# 新しいリモートリポジトリにプッシュ
git remote add origin <NEW_REPO_URL>
git push -u origin main
```

### オプション3: 何もしない（推奨）

現在のコードには機密情報が含まれていないため、以下の理由で何もしないことを推奨します：

1. **現在のコードは安全**: すべての機密情報は削除済み
2. **gitleaksが保護**: 新しいコミットでシークレットが追加されるのを防ぐ
3. **履歴の書き換えはリスク**: 他の開発者との同期が困難になる

## 今後の対策

### 1. gitleaksによる自動スキャン

すでに設定済み：

- **pre-commitフック**: コミット前にスキャン
- **GitHub Actions**: プッシュ時にスキャン

### 2. .gitignoreの活用

機密情報を含むファイルは`.gitignore`に追加：

```
.envrc
.env
*.pem
*.key
```

### 3. AWS Secrets Managerの使用

本番環境では環境変数ではなくSecrets Managerを使用：

```python
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']
```

### 4. GitHub Secretsの使用

CI/CDでは環境変数ではなくGitHub Secretsを使用：

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
```

## 参考リンク

- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
- [Removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [Gitleaks](https://github.com/gitleaks/gitleaks)
- [git-filter-repo](https://github.com/newren/git-filter-repo)

## まとめ

現在のコードは安全であり、gitleaksによる保護も設定済みです。過去の履歴に含まれる情報は、リポジトリが公開されていない限り問題ありません。

もしリポジトリを公開する予定がある場合は、オプション2（新しいリポジトリの作成）を推奨します。
