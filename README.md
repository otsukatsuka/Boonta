![Lint](https://github.com/otsukatsuka/Boonta/actions/workflows/lint.yml/badge.svg)
![Tests](https://github.com/otsukatsuka/Boonta/actions/workflows/test.yml/badge.svg)

# Boonta v2 - JRDB競馬予測AIシステム

JRDBデータを使った競馬展開予想・予測AIシステム。JRDB固定長ファイル（KYI/SED/HJC）をパースし、AutoGluon（Modal.com）による機械学習で複勝確率を予測。展開予想テキストと回収率評価を出力するCLIパイプライン。

## セットアップ

```bash
# Python 3.10+ が必要
python3.10 -m venv .venv
source .venv/bin/activate
pip3 install -e ".[dev]"
```

## 使い方

### JRDBファイルのダウンロード

```bash
# 単日ダウンロード
python cli.py download --type KYI --date 260405

# 日付範囲
python cli.py download --type SED --date-range 20250101 20251231
```

### パース（raw → CSV）

```bash
python cli.py parse --type KYI --date 260405
python cli.py parse --all  # data/raw/ 内の全ファイル
```

### モデル学習

```bash
python cli.py train --date-range 20200101 20251231 --time-limit 1800
```

### 予測 + 展開予想

```bash
python cli.py predict --date 260405
python cli.py predict --date 260405 --race 11  # 特定レースのみ
python cli.py predict --date 260405 --no-ml    # ML予測なし（展開予想のみ）
```

### 回収率評価

```bash
python cli.py evaluate --date-range 20250101 20251231 --strategy fukusho_top3
python cli.py evaluate --date-range 20250101 20251231 --strategy umaren_top2
python cli.py evaluate --date-range 20250101 20251231 --strategy sanrenpuku_top3
```

## アーキテクチャ

```
JRDB Server → data/raw/ → data/processed/ → Features → Modal.com → 展開予想 + ROI
  download/     parser/      features/                    predict/
```

| ディレクトリ | 役割 |
|---|---|
| `src/download/` | JRDBダウンローダー（HTTP認証 + ZIP/LZH解凍） |
| `src/parser/` | 固定長ファイルパーサー（KYI/SED/HJC） |
| `src/features/` | フィーチャーエンジニアリング（~35特徴量） |
| `src/model/` | Modal関数（AutoGluon学習/推論） |
| `src/predict/` | 予測パイプライン・展開予想・ROI評価 |
| `config/` | 設定（Pydantic BaseSettings） |

## テスト

```bash
pytest                              # 全テスト（125テスト）
pytest tests/test_parser/ -v        # パーサーテスト
pytest tests/test_features/ -v      # フィーチャーテスト
pytest --cov=src --cov-report=html  # カバレッジ
```

## 品質チェック

```bash
ruff check src/ config/ cli.py
mypy src/ config/ cli.py
```
