# セットアップ

Boonta v2 を動かすための環境構築手順。

## 前提

- macOS / Linux（Windows は未検証）
- Python **3.10**（3.11 も動作確認済み、3.12 以降は AutoGluon 互換性のため未推奨）
- JRDB 会員アカウント（[https://www.jrdb.com/member/](https://www.jrdb.com/member/) で登録）
- Modal アカウント（[https://modal.com/](https://modal.com/) で登録）

## 手順

### 1. リポジトリ取得

```bash
git clone git@github.com:otsukatsuka/Boonta.git
cd Boonta
```

### 2. 仮想環境とパッケージインストール

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip3 install -e ".[dev]"
```

`.venv/` は `.gitignore` 済み。`pip3` を使う（環境による `pip` / `pip3` の混在を避けるため）。

### 3. 環境変数（`.env`）

`.env.example` をコピーして JRDB 認証情報を設定:

```bash
cp .env.example .env
# .env を編集
```

```env
JRDB_USER=your_username_here
JRDB_PASS=your_password_here
```

> **重要**: `.env` は `.gitignore` 対象。**絶対にコミットしない**。

`config/settings.py` でその他の設定値（Modal App 名、データパスなど）を上書きしたい場合も `.env` に書く（Pydantic `BaseSettings` が自動的に読み込む）。

### 4. Modal セットアップ

```bash
pip3 install modal  # 既に [.dev] でインストール済み
modal token new     # ブラウザでアカウント認証
```

初回は Modal Image をビルドする必要がある:

```bash
modal deploy src/model/functions.py
```

App `boonta-ml` がデプロイされ、関数 `train_model` / `predict` / `get_model_status` / `get_feature_importance` が利用可能になる。

### 5. データディレクトリ

`data/` は自動生成（コマンド実行時）。手動でも作成可:

```bash
mkdir -p data/raw data/processed
```

`data/` も `.gitignore` 対象。**JRDB 由来のデータをコミットしない**。

## 動作確認

```bash
# CLI ヘルプ表示
python cli.py --help
python cli.py download --help

# テスト実行
pytest

# 品質チェック
ruff check src/ cli.py config/
mypy src/ cli.py config/
```

## 関連ドキュメント

- 開発フロー・テスト方針: [docs/DEVELOPMENT.md](DEVELOPMENT.md)
- Modal 関連の運用: [docs/MODAL.md](MODAL.md)
- CLI コマンド一覧: [docs/CLI.md](CLI.md)
