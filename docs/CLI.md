# CLI リファレンス

Boonta v2 の CLI（`cli.py`、click ベース）の全コマンドリファレンス。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| [`download`](#download) | JRDB ファイルのダウンロード |
| [`parse`](#parse) | 固定長 → CSV 変換 |
| [`train`](#train) | Modal 上で ML モデル学習 |
| [`predict`](#predict) | 予測実行 + 展開予想出力 |
| [`evaluate`](#evaluate) | ROI 評価（戦略別） |

すべて `python cli.py <command> [options]` で起動する。

---

## `download`

JRDB サーバから ZIP / LZH ファイルをダウンロードして `data/raw/` に展開する。`.env` に `JRDB_USER` / `JRDB_PASS` が必要。

```bash
python cli.py download --type {KYI|SED|HJC} (--date YYMMDD | --date-range YYYYMMDD YYYYMMDD)
```

| オプション | 必須 | 説明 |
|-----------|------|------|
| `--type` | ✅ | `KYI` / `SED` / `HJC` のいずれか |
| `--date` | △ | 単日。`YYMMDD` 形式（例 `260405`） |
| `--date-range` | △ | 範囲。`YYYYMMDD YYYYMMDD` 形式（例 `20250101 20251231`） |

`--date` と `--date-range` のどちらか一方を指定する。

### 例

```bash
# 単日
python cli.py download --type KYI --date 260405

# 期間
python cli.py download --type SED --date-range 20250101 20251231
```

---

## `parse`

`data/raw/` 配下の固定長ファイルをパースして `data/processed/` に CSV 出力する。

```bash
python cli.py parse (--type {KYI|SED|HJC} --date YYMMDD | --all)
```

| オプション | 必須 | 説明 |
|-----------|------|------|
| `--type` | △ | `KYI` / `SED` / `HJC`（`--all` 指定時は不要） |
| `--date` | △ | 単日（`--type` と組み合わせ） |
| `--all` | △ | `data/raw/` 配下の全ファイルを一括パース |

### 例

```bash
# 単日・単タイプ → data/processed/kyi_260405.csv
python cli.py parse --type KYI --date 260405

# 全ファイル一括 → data/processed/{kyi,sed,hjc}.csv
python cli.py parse --all
```

---

## `train`

`data/raw/` の KYI + SED から学習データを生成し、Modal 上で AutoGluon を学習させる。

```bash
python cli.py train --date-range YYYYMMDD YYYYMMDD [--time-limit 1800]
```

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `--date-range` | ✅ | — | 学習データ期間（`YYYYMMDD YYYYMMDD`） |
| `--time-limit` | — | `1800` | AutoGluon 学習タイムリミット（秒） |

### 例

```bash
python cli.py train --date-range 20200101 20241231 --time-limit 1800
```

学習結果は Modal Volume `boonta-models` の `jrdb_predictor` に保存される。

---

## `predict`

指定日の KYI を読み込み、展開予想と ML 予測（is_place 確率）、EV ランキングと買い目推薦を出力する。

```bash
python cli.py predict --date YYMMDD [--race N] [--no-ml] [--no-bet] [--ev-threshold 1.0]
```

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `--date` | ✅ | — | 予測対象日（`YYMMDD`） |
| `--race` | — | 全レース | 特定レース番号のみ予測 |
| `--no-ml` | — | `False` | ML 予測をスキップ（展開予想のみ表示） |
| `--no-bet` | — | `False` | EV ランキング・買い目セクションを非表示 |
| `--ev-threshold` | — | `1.0` | EV ピックの閾値（`1.0` = ブレイクイーブン） |

### 例

```bash
# 当日の全レースを予測
python cli.py predict --date 260405

# 11R のみ
python cli.py predict --date 260405 --race 11

# 展開予想のみ（ML 不要）
python cli.py predict --date 260405 --no-ml

# EV 閾値を厳しめに
python cli.py predict --date 260405 --ev-threshold 1.2
```

---

## `evaluate`

過去レースで予測 → HJC 払戻データと突き合わせて ROI を算出。

```bash
python cli.py evaluate --date-range YYYYMMDD YYYYMMDD [--strategy <戦略>] [--ev-threshold 1.0]
```

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `--date-range` | ✅ | — | 評価期間 |
| `--strategy` | — | `fukusho_top3` | 後述の戦略一覧から選択 |
| `--ev-threshold` | — | `1.0` | EV 系戦略の閾値（非 EV 戦略では無視） |

### 戦略一覧

| 戦略 | 説明 |
|------|------|
| `fukusho_top3` | ML 予測上位 3 頭の複勝に各 100 円 |
| `umaren_top2` | ML 予測上位 2 頭の馬連 1 点 100 円 |
| `sanrenpuku_top3` | ML 予測上位 3 頭の 3 連複 1 点 100 円 |
| `ev_tansho` | EV 単 > 閾値の馬に単勝 100 円ずつ |
| `ev_fukusho` | EV 複 > 閾値の馬に複勝 100 円ずつ |
| `ev_sanrenpuku_nagashi` | EV 複 > 閾値の馬を軸に、EV 単 TOP5 を相手に 3 連複 1 頭流し |

戦略の詳細・ロジックは [docs/EVALUATION.md](EVALUATION.md) を参照。

### 例

```bash
# ベースライン
python cli.py evaluate --date-range 20250101 20251228 --strategy fukusho_top3

# EV 戦略
python cli.py evaluate --date-range 20250101 20251228 --strategy ev_tansho --ev-threshold 1.0
```

### 出力

```
========================================
戦略: ev_tansho
レース数: 3,453
購入レース数: 1,802
投資額: 540,000円
回収額: 525,300円
回収率: 97.3%
的中数: 287
========================================
```

> **注意**: `evaluate` は各レースごとに Modal `predict` を呼ぶため、2025 年通年で戦略あたり 5〜15 分かかる。
