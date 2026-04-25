![Lint](https://github.com/otsukatsuka/Boonta/actions/workflows/lint.yml/badge.svg)
![Tests](https://github.com/otsukatsuka/Boonta/actions/workflows/test.yml/badge.svg)

# Boonta v2 — JRDB 競馬予測 AI システム

JRDB データを使った競馬展開予想・予測 AI システム。JRDB 固定長ファイル（KYI / SED / HJC）をパースし、AutoGluon（Modal.com）による機械学習で複勝確率を予測。展開予想テキストと回収率評価、EV ベースの買い目推薦を出力する CLI パイプライン。

## 主な機能

- **JRDB ファイル取り込み**: HTTP 認証でダウンロード、固定長レコードを CSV に変換
- **特徴量エンジニアリング**: KYI 由来の ~35 特徴量（展開コア、スピード指標、適性、派生）
- **ML 予測**: Modal 上で AutoGluon を学習・推論。`is_place`（3 着以内）の確率を出す
- **展開予想**: ペース・位置取り・有利/不利馬・穴馬注意のテキスト生成
- **EV ベース買い目推薦**: 期待値プラスの馬をピック、単複・馬連 BOX・3 連複流し
- **ROI 評価**: 6 戦略（ML ベース 3 種 + EV ベース 3 種）でバックテスト

## クイックスタート

```bash
# セットアップ
python3.10 -m venv .venv
source .venv/bin/activate
pip3 install -e ".[dev]"

# 認証情報を設定
cp .env.example .env
# .env を編集して JRDB_USER / JRDB_PASS を入れる

# Modal アカウント認証（初回のみ）
modal token new
modal deploy src/model/functions.py

# 予測実行（要：data/raw/KYI260405.txt が手元にあること）
python cli.py download --type KYI --date 260405
python cli.py predict --date 260405 --no-ml
```

詳細は [docs/SETUP.md](docs/SETUP.md) を参照。

## アーキテクチャ概要

```
JRDB Server → data/raw/ → data/processed/ → Features → Modal.com → 展開予想 + ROI / EV
  download/     parser/      features/                    predict/
```

| ディレクトリ | 役割 |
|---|---|
| `src/download/` | JRDB ダウンローダー（HTTP 認証 + ZIP/LZH 解凍） |
| `src/parser/` | 固定長ファイルパーサー（KYI/SED/HJC） |
| `src/features/` | 特徴量エンジニアリング（~35 特徴量） |
| `src/model/` | Modal 関数（AutoGluon 学習/推論） |
| `src/predict/` | 予測ランナー、展開予想、ROI、買い目推薦 |
| `config/` | 設定（Pydantic BaseSettings） |

## ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [docs/SETUP.md](docs/SETUP.md) | 環境構築、`.env`、Modal セットアップ |
| [docs/CLI.md](docs/CLI.md) | CLI コマンドリファレンス |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | システム設計、データフロー、モジュール責務 |
| [docs/FEATURES.md](docs/FEATURES.md) | 特徴量設計（6 カテゴリ・~35 特徴量） |
| [docs/MODAL.md](docs/MODAL.md) | Modal 統合、関数仕様、運用 Tips |
| [docs/EVALUATION.md](docs/EVALUATION.md) | ROI / EV 戦略の解説とバックテスト |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | 開発フロー、テスト、コーディング規約 |

## 注意事項

- **JRDB データの取り扱い**: JRDB の固定長ファイル・処理済み CSV・公式仕様書はすべて `.gitignore` 対象。**コミット禁止**。会員規約を遵守すること
- **`.env` / 認証情報**: `JRDB_USER` / `JRDB_PASS` をはじめとする認証情報は `.env` のみに置く
- **AutoGluon preset**: `best_quality` のみ使用。`extreme` は禁止
- **モデル学習データ**: `data/`、`models/` は `.gitignore` 対象

## ライセンス

未設定（個人プロジェクト）。
