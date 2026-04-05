# Boonta Ver.2 設計書

## 1. プロジェクト概要

JRDBデータを使った競馬展開予想AIシステム。  
v1のnetkeiba scraping + FastAPI + React構成から、JRDB固定長ファイル + CLIパイプラインに刷新する。  
AutoGluon (Modal.com) による機械学習基盤はv1から継承。

### v1 → v2 変更点

| 項目 | v1 | v2 |
|------|----|----|
| データソース | netkeiba.com (HTML scraping) | JRDB (固定長テキスト) |
| アーキテクチャ | FastAPI + React + SQLite | Python CLI パイプライン |
| MLフィーチャー | 34個 (scraping由来) | ~35個 (JRDB指数ベース) |
| 展開予想 | ルールベース (pace.py) | JRDB展開予想データ + ML |
| 実行環境 | Docker / ローカルサーバ | CLI + Modal.com |
| 回収率評価 | なし | HJC払戻データで算出 |

### 継承するv1資産

- Modal.com インフラ（App "boonta-ml"、Volume "boonta-models"）
- AutoGluon設定（binary classification、ROC-AUC、best_quality preset）
- Modal functions パターン（train_model / predict / get_model_status / get_feature_importance）
- 自己完結型Modal関数（外部importなし、前処理インライン）

---

## 2. ディレクトリ構成

```
boonta/
├── CLAUDE.md                  # Claude Code向け指示書
├── README.md
├── .gitignore
├── .env                       # JRDB_USER, JRDB_PASS (.gitignore対象)
├── pyproject.toml             # 依存関係・プロジェクト設定
├── cli.py                     # CLIエントリーポイント (click)
├── config/
│   ├── __init__.py
│   └── settings.py            # Pydantic BaseSettings
├── data/
│   ├── raw/                   # JRDBダウンロードファイル (.gitignore対象)
│   └── processed/             # 変換済みCSV (.gitignore対象)
├── src/
│   ├── __init__.py
│   ├── download/
│   │   ├── __init__.py
│   │   └── jrdb.py            # JRDBダウンローダー
│   ├── parser/
│   │   ├── __init__.py
│   │   ├── spec.py            # FieldSpec定義 + 型変換ルール
│   │   ├── engine.py          # 汎用固定長パーサーエンジン
│   │   ├── kyi.py             # KYI (競走馬データ) フィールド仕様
│   │   ├── sed.py             # SED (成績データ) フィールド仕様
│   │   └── hjc.py             # HJC (払戻データ) フィールド仕様
│   ├── features/
│   │   ├── __init__.py
│   │   ├── columns.py         # フィーチャーカラム定義・デフォルト値
│   │   ├── engineering.py     # フィーチャーエンジニアリング本体
│   │   └── derived.py         # 派生フィーチャー計算
│   ├── model/
│   │   ├── __init__.py
│   │   ├── functions.py       # Modal関数 (train, predict, status)
│   │   ├── image.py           # Modal Image定義
│   │   └── client.py          # ModalClient (CLI用同期呼び出し)
│   └── predict/
│       ├── __init__.py
│       ├── runner.py           # 予測オーケストレーター
│       ├── tenkai.py           # 展開予想フォーマッター
│       └── roi.py              # 回収率評価 (HJC払戻ベース)
├── tests/
│   ├── conftest.py
│   ├── fixtures/               # テスト用JRDBレコードバイナリ
│   ├── test_parser/
│   ├── test_features/
│   ├── test_model/
│   └── test_predict/
└── notebooks/                  # 分析用 (.gitignore対象)
```

---

## 3. データパイプライン

### 全体フロー

```
┌──────────────┐    ┌──────────────┐    ┌──────────────────┐    ┌────────────┐
│ JRDB Server  │───>│ data/raw/    │───>│ data/processed/  │───>│ Features   │
│ (ZIP/LZH)    │    │ KYI*.txt     │    │ kyi.csv          │    │ DataFrame  │
│              │    │ SED*.txt     │    │ sed.csv          │    │            │
│              │    │ HJC*.txt     │    │ hjc.csv          │    │            │
└──────────────┘    └──────────────┘    └──────────────────┘    └─────┬──────┘
   download/            parser/              features/               │
                                                              ┌──────┘
                                                              │
                ┌─────────────────────────────────────────────┘
                │
          ┌─────▼──────┐         ┌─────────────────┐
          │ Training:  │────────>│  Modal.com      │
          │ CSV string │         │  AutoGluon      │
          ├────────────┤         │  train_model()  │
          │ Prediction:│────────>│  predict()      │
          │ JSON       │         └────────┬────────┘
          └────────────┘                  │
                                ┌─────────▼────────┐
                                │  展開予想 Output  │
                                │  + ROI Evaluation │
                                └──────────────────┘
```

### 学習フロー

```
cli.py train
  → download KYI + SED (指定日付範囲)
  → parse → CSV
  → build_training_features(kyi_df, sed_df)
    → JOIN on race_key + 馬番
    → is_place = (着順 <= 3) をラベルとして付与
    → 派生フィーチャー追加
  → CSV文字列化 → Modal train_model() に送信
```

### 予測フロー

```
cli.py predict --date 2026-04-05
  → download KYI (当日分)
  → parse → DataFrame
  → build_prediction_features(kyi_df)
  → JSON化 → Modal predict() で is_place確率取得
  → format_tenkai() で展開予想テキスト出力
```

### 回収率評価フロー

```
cli.py evaluate --date-range 2025-01-01 2025-12-31
  → 予測結果 + parse HJC → evaluate_roi()
  → 複勝/馬連/3連複の各戦略でROI算出
```

---

## 4. パーサー設計

### 4.1 フィールド仕様定義 (`src/parser/spec.py`)

```python
@dataclass
class FieldSpec:
    name: str           # カラム名
    offset: int         # 1-based バイトオフセット (仕様書準拠)
    length: int         # バイト長
    field_type: str     # "numeric" | "text" | "decimal" | "hex"
    scale: int = 0      # 小数桁数 (例: ZZ9.9 → scale=1)
    signed: bool = False  # マイナス符号あり
    description: str = ""
```

### 4.2 型変換ルール

JRDBのTYPE列に対応:

| JRDB TYPE | field_type | 変換ロジック |
|-----------|-----------|-------------|
| `9` (数字, 0→0) | `"numeric"` | strip → int, 空白→None |
| `Z` (数字, 0→空白) | `"numeric"` | strip spaces → int, 全空白→None |
| `ZZ9.9` | `"decimal"` | strip → float, scale=1 |
| `X` (文字) | `"text"` | CP932→UTF-8, strip trailing spaces |
| `F` (16進数) | `"hex"` | hex digit (日フィールド: 1-9, a-f) |

### 4.3 パースエンジン (`src/parser/engine.py`)

```python
def parse_record(line: bytes, fields: list[FieldSpec]) -> dict[str, Any]:
    """1レコードをパース"""
    record = {}
    for f in fields:
        raw = line[f.offset - 1 : f.offset - 1 + f.length]  # 1-based → 0-based
        text = raw.decode("cp932", errors="replace").strip()
        record[f.name] = coerce(text, f.field_type, f.scale, f.signed)
    return record

def parse_file(path: Path, fields: list[FieldSpec], record_length: int) -> pd.DataFrame:
    """固定長ファイル全体をDataFrameに変換"""
    with open(path, "rb") as fh:
        raw = fh.read()
    records = []
    # record_lengthにはCRLF(2バイト)を含む
    for i in range(0, len(raw), record_length):
        line = raw[i : i + record_length]
        if len(line) >= record_length - 2:
            records.append(parse_record(line, fields))
    return pd.DataFrame(records)
```

### 4.4 レースキー構造

```
場コード(2) + 年(2) + 回(1) + 日(1, hex) + R(2) = 8文字
```

- KYI/SED: `race_key + 馬番` でJOIN (馬単位レコード)
- HJC: `race_key` のみ (レース単位レコード)

```python
def build_race_key(record: dict) -> str:
    """レースキーを構築。日フィールドはhex値をそのまま使用"""
    return f"{record['場コード']:02d}{record['年']:02d}{record['回']}{record['日']}{record['R']:02d}"
```

### 4.5 KYI主要フィールド (全80+フィールド中、ML関連抜粋)

| フィールド | offset | 長さ | 型 | 用途 |
|-----------|--------|------|------|------|
| 場コード | 1 | 2 | numeric | レースキー |
| 年 | 3 | 2 | numeric | レースキー |
| 回 | 5 | 1 | numeric | レースキー |
| 日 | 6 | 1 | hex | レースキー |
| R | 7 | 2 | numeric | レースキー |
| 馬番 | 9 | 2 | numeric | 馬識別 |
| 血統登録番号 | 11 | 8 | text | 馬リンクキー |
| 馬名 | 19 | 36 | text | 表示用 |
| IDM | 55 | 5 | decimal(1) | 総合指数 |
| 騎手指数 | 60 | 5 | decimal(1) | 騎手能力 |
| 情報指数 | 65 | 5 | decimal(1) | 情報評価 |
| 総合指数 | 85 | 5 | decimal(1) | 総合評価 |
| 脚質 | 90 | 1 | numeric | 走法タイプ |
| 距離適性 | 91 | 1 | numeric | 距離適性 |
| 基準オッズ | 96 | 5 | decimal(1) | オッズ |
| 基準人気順位 | 101 | 2 | numeric | 人気 |
| 調教指数 | 145 | 5 | decimal(1) | 調教評価 |
| 厩舎指数 | 150 | 5 | decimal(1) | 厩舎力 |
| 重適正コード | 166 | 1 | numeric | 重馬場適性 |
| テン指数 | 359 | 5 | decimal(1) | 前半速度 |
| ペース指数 | 364 | 5 | decimal(1) | 中間ペース |
| 上がり指数 | 369 | 5 | decimal(1) | 終盤速度 |
| 位置指数 | 374 | 5 | decimal(1) | 位置取り指数 |
| ペース予想 | 379 | 1 | text | H/M/S |
| 道中順位 | 380 | 2 | numeric | 展開コア |
| 道中差 | 382 | 2 | numeric | 0.1秒単位 |
| 道中内外 | 384 | 1 | numeric | 2:内〜5:大外 |
| 後3F順位 | 385 | 2 | numeric | 展開コア |
| 後3F差 | 387 | 2 | numeric | 0.1秒単位 |
| 後3F内外 | 389 | 1 | numeric | 2:内〜5:大外 |
| ゴール順位 | 390 | 2 | numeric | 展開コア |
| ゴール差 | 392 | 2 | numeric | 0.1秒単位 |
| ゴール内外 | 394 | 1 | numeric | 1:最内〜5:大外 |
| 展開記号 | 395 | 1 | text | 展開記号コード |
| 馬スタート指数 | 520 | 4 | decimal(1) | 出遅れリスク |
| 馬出遅率 | 524 | 4 | decimal(1) | 出遅れ率(%) |
| 万券指数 | 535 | 3 | numeric | 穴馬指標 |
| 枠番 | 324 | 1 | numeric | 枠番 |
| 負担重量 | 184 | 3 | numeric | 0.1kg単位 |
| 取消フラグ | 403 | 1 | numeric | 1:取消 |

### 4.6 SED主要フィールド

| フィールド | offset | 長さ | 型 | 用途 |
|-----------|--------|------|------|------|
| 着順 | 141 | 2 | numeric | MLラベル |
| 異常区分 | 143 | 1 | numeric | 除外判定 |
| タイム | 144 | 4 | numeric | 走破タイム |
| 確定単勝オッズ | 175 | 6 | decimal(1) | 実オッズ |
| 馬場差 | 189 | 3 | numeric | 馬場補正 |
| 前不利 | 204 | 3 | numeric | ノイズ除去 |
| 中不利 | 207 | 3 | numeric | ノイズ除去 |
| 後不利 | 210 | 3 | numeric | ノイズ除去 |
| コース取り | 216 | 1 | numeric | 1:最内〜5:大外 |
| レースペース | 222 | 1 | text | H/M/S (実績) |
| 馬ペース | 223 | 1 | text | H/M/S (実績) |
| テン指数 | 224 | 5 | decimal(1) | 実績値 |
| 上がり指数 | 229 | 5 | decimal(1) | 実績値 |
| ペース指数 | 234 | 5 | decimal(1) | 実績値 |
| コーナー順位1〜4 | 309 | 2×4 | numeric | 通過順位 |
| 前3Fタイム | 259 | 3 | numeric | 0.1秒単位 |
| 後3Fタイム | 262 | 3 | numeric | 0.1秒単位 |
| 馬体重 | 333 | 3 | numeric | 馬体重 |
| 馬体重増減 | 336 | 3 | text | 符号+数字 |
| レース脚質 | 341 | 1 | text | 脚質コード |
| 4角コース取り | 370 | 1 | numeric | 1:最内〜5:大外 |
| 距離 | 63 | 4 | numeric | レース距離 |
| 芝ダ障害コード | 67 | 1 | numeric | 1:芝, 2:ダ, 3:障 |
| 馬場状態 | 70 | 2 | numeric | 馬場状態 |
| グレード | 80 | 1 | numeric | G1等 |
| 頭数 | 131 | 2 | numeric | 出走頭数 |

### 4.7 HJC主要フィールド

| フィールド | OCC | offset | 構造 |
|-----------|-----|--------|------|
| 単勝払戻 | 3回 | 9 | 馬番(2) + 払戻金(7) × 3 |
| 複勝払戻 | 5回 | 36 | 馬番(2) + 払戻金(7) × 5 |
| 馬連払戻 | 3回 | 108 | 組合せ(4) + 払戻金(8) × 3 |
| ワイド払戻 | 7回 | 144 | 組合せ(4) + 払戻金(8) × 7 |
| 馬単払戻 | 6回 | 228 | 組合せ(4) + 払戻金(8) × 6 |
| 3連複払戻 | 3回 | 300 | 組合せ(6) + 払戻金(8) × 3 |
| 3連単払戻 | 6回 | 342 | 組合せ(6) + 払戻金(9) × 6 |

※ HJCは繰り返し構造（OCC）の解析が必要。パーサーで展開してフラットなカラムに変換。

---

## 5. フィーチャーエンジニアリング

### 5.1 MLフィーチャー一覧

#### カテゴリ1: 展開コア (KYI由来)

| フィーチャー名 | JRDBフィールド | 型 |
|--------------|---------------|------|
| `pace_forecast` | ペース予想 | categorical (H/M/S) |
| `mid_position` | 道中順位 | numeric |
| `mid_gap` | 道中差 | numeric |
| `mid_position_io` | 道中内外 | numeric (2-5) |
| `late3f_position` | 後3F順位 | numeric |
| `late3f_gap` | 後3F差 | numeric |
| `late3f_io` | 後3F内外 | numeric (2-5) |
| `goal_position` | ゴール順位 | numeric |
| `goal_gap` | ゴール差 | numeric |
| `goal_io` | ゴール内外 | numeric (1-5) |
| `tenkai_symbol` | 展開記号 | categorical |

#### カテゴリ2: スピード指標 (KYI予想値 / SED実績値)

| フィーチャー名 | JRDBフィールド | 型 |
|--------------|---------------|------|
| `ten_index` | テン指数 | float |
| `pace_index` | ペース指数 | float |
| `agari_index` | 上がり指数 | float |
| `position_index` | 位置指数 | float |
| `idm` | IDM | float |

#### カテゴリ3: 馬・厩舎・騎手指数 (KYI由来)

| フィーチャー名 | JRDBフィールド | 型 |
|--------------|---------------|------|
| `jockey_index` | 騎手指数 | float |
| `info_index` | 情報指数 | float |
| `overall_index` | 総合指数 | float |
| `training_index` | 調教指数 | float |
| `stable_index` | 厩舎指数 | float |

#### カテゴリ4: 適性・リスク (KYI由来)

| フィーチャー名 | JRDBフィールド | 型 |
|--------------|---------------|------|
| `running_style` | 脚質 | categorical (1-4) |
| `distance_aptitude` | 距離適性 | categorical |
| `heavy_track_code` | 重適正コード | categorical |
| `start_index` | 馬スタート指数 | float |
| `gate_miss_rate` | 馬出遅率 | float |
| `upset_index` | 万券指数 | numeric |

#### カテゴリ5: レース条件

| フィーチャー名 | JRDBフィールド | 型 |
|--------------|---------------|------|
| `horse_number` | 馬番 | numeric |
| `waku` | 枠番 | numeric |
| `odds` | 基準オッズ | float |
| `popularity` | 基準人気順位 | numeric |
| `weight_carried` | 負担重量 | float (÷10) |

#### カテゴリ6: 派生フィーチャー (計算)

| フィーチャー名 | 計算式 | 意味 |
|--------------|--------|------|
| `speed_balance` | テン指数 - 上がり指数 | 正=前傾, 負=差し型 |
| `position_delta` | ゴール順位 - 道中順位 | 負=追い上げ, 正=後退 |
| `io_shift` | ゴール内外 - 道中内外 | 内外移動 |
| `log_odds` | log(基準オッズ) | オッズ対数 |
| `risk_score` | 馬出遅率 × (1 - スタート指数/10) | 出遅れリスク |
| `race_head_count` | レース内KYIレコード数 | 出走頭数 |

### 5.2 学習データ構築

```python
def build_training_features(kyi_df: pd.DataFrame, sed_df: pd.DataFrame) -> pd.DataFrame:
    """
    KYI (前日予想) と SED (実績) を race_key + 馬番 でJOIN。
    KYI: 予測時に利用可能なフィーチャー (入力)
    SED: ラベル (着順 → is_place) + 実績データ (検証用)
    """
    # 1. 両方にrace_keyカラムを構築
    # 2. race_key + 馬番 でmerge
    # 3. is_place = (着順 <= 3) をラベルとして追加
    # 4. 異常区分 != 0 のレコードを除外 (取消・失格等)
    # 5. 派生フィーチャー追加
    # 6. FEATURE_COLUMNS + "is_place" のみ返す
```

**設計方針**: 学習時のフィーチャーはKYI由来のみ使用（予測時にも利用可能なデータに限定）。SEDはラベル（is_place）と異常区分フィルタにのみ使用。将来的に同一馬の過去SED実績をルックバックフィーチャーとして追加可能。

---

## 6. モデル設計

### 6.1 v1 Modal関数の継承

v1 (`backend/modal_app/functions.py`) のパターンをそのまま踏襲:

| 関数 | 用途 | 変更点 |
|------|------|--------|
| `train_model()` | AutoGluon学習 | フィーチャー前処理をJRDB対応に |
| `predict()` | is_place確率予測 | 同上 |
| `get_model_status()` | モデル状態確認 | model_name変更のみ |
| `get_feature_importance()` | 特徴量重要度 | 変更なし |

### 6.2 AutoGluon設定

| 項目 | 値 |
|------|-----|
| problem_type | binary |
| eval_metric | roc_auc |
| presets | best_quality |
| time_limit | 1800秒 (デフォルト) |
| label | is_place |
| model_name | jrdb_predictor |

### 6.3 Modal構成

| 項目 | 値 |
|------|-----|
| App名 | boonta-ml |
| Image | debian_slim + Python 3.12 + AutoGluon 1.5.1 |
| Volume | boonta-models |
| 学習: memory | 8GB, CPU 4.0, timeout 7200秒 |
| 推論: memory | 4GB, timeout 60秒 |

### 6.4 フィーチャー前処理 (Modal内インライン)

```python
# Modal functions.py 内に自己完結で定義
def preprocess_features(df):
    categorical_cols = ["pace_forecast", "running_style", "distance_aptitude",
                        "heavy_track_code", "tenkai_symbol"]
    numerical_defaults = {
        "idm": 50.0, "jockey_index": 50.0, "overall_index": 50.0,
        "ten_index": 50.0, "pace_index": 50.0, "agari_index": 50.0,
        "position_index": 50.0, "training_index": 50.0, "stable_index": 50.0,
        "info_index": 50.0, "odds": 10.0, "popularity": 8,
        "horse_number": 5, "waku": 4, "weight_carried": 55.0,
        "mid_position": 8, "late3f_position": 8, "goal_position": 8,
        "mid_gap": 5, "late3f_gap": 5, "goal_gap": 5,
        "mid_position_io": 3, "late3f_io": 3, "goal_io": 3,
        "start_index": 50.0, "gate_miss_rate": 5.0, "upset_index": 50,
    }
    # ... fill NaN, cast types
```

### 6.5 ModalClient (CLI用)

v1はasync (FastAPI用) だったが、v2はsync (CLI用):

```python
class ModalClient:
    def train(self, csv_data: str, time_limit: int = 1800, presets: str = "best_quality") -> dict:
        train_fn = modal.Function.from_name("boonta-ml", "train_model")
        return train_fn.remote(training_data_csv=csv_data, model_name="jrdb_predictor",
                               time_limit=time_limit, presets=presets)

    def predict(self, features: list[dict]) -> dict:
        predict_fn = modal.Function.from_name("boonta-ml", "predict")
        return predict_fn.remote(features_json=json.dumps(features), model_name="jrdb_predictor")
```

---

## 7. 展開予想出力

### 7.1 出力フォーマット

```
══════════════════════════════════════════════
【展開予想】2026/04/05 阪神11R 大阪杯 (G1) 芝2000m
══════════════════════════════════════════════

■ ペース予想: ミドル (M)
  逃げ馬: 3番ドウデュース (テン指数: 52.3)
  先行争い: 3番, 7番, 12番

■ 位置取り予想
  馬番  馬名            脚質  道中  後3F  ゴール  内外
    3  ドウデュース      逃げ    1     2      1    内
    7  リバティアイランド 先行    3     3      2    中
   12  タスティエーラ    差し    8     5      3    外
  ...

■ ML予測 (is_place確率)
  1位:  3番 ドウデュース      78.2%
  2位:  7番 リバティアイランド 65.1%
  3位: 12番 タスティエーラ    58.3%
  ...

■ 有利馬・不利馬
  ★有利: 3番 (逃げ有利のミドルペース + 内枠)
  ★有利: 12番 (上がり指数1位, 差し展開向き)
  ▲不利: 5番 (出遅率12.5%, スタート指数低)

■ 馬場コメント
  良馬場。内有利傾向。

■ 穴馬注意
  14番 (万券指数: 82) -- 展開一つで激走あり
```

### 7.2 構成要素

| セクション | データソース | ロジック |
|-----------|------------|---------|
| ペース予想 | KYI ペース予想 | 各馬のH/M/S分布から決定 |
| 位置取り | KYI 展開予想データ | 道中順位/後3F順位/ゴール順位をそのまま表示 |
| ML予測 | Modal predict() | is_place確率でランキング |
| 有利/不利 | KYI + 派生フィーチャー | 脚質×ペース×内外の組合せ判定 |
| 馬場コメント | KYI 重適正コード | 馬場適性とペースの関連 |
| 穴馬 | KYI 万券指数 | 万券指数上位をマーク |

---

## 8. 回収率評価

### 8.1 評価ロジック (`src/predict/roi.py`)

```python
def evaluate_roi(predictions_df, hjc_df, strategy: str = "fukusho_top3") -> dict:
    """
    予測結果とHJC払戻データで回収率を算出。

    strategies:
      - fukusho_top3: is_place確率上位3頭の複勝を各100円
      - umaren_top2: 上位2頭の馬連を100円
      - sanrenpuku_top3: 上位3頭の3連複を100円
    """
    # 1. 予測結果からrace_key別に上位N頭を選出
    # 2. HJCの該当馬番と照合
    # 3. 的中時の払戻金を加算
    # 4. 投資金額と回収金額からROIを算出
    return {"strategy": strategy, "total_bets": ..., "total_return": ..., "roi": ...}
```

---

## 9. CLIコマンド

```bash
# JRDBファイルダウンロード
python cli.py download --type KYI --date 2026-04-05
python cli.py download --type SED --date-range 2025-01-01 2025-12-31

# パース (raw → processed CSV)
python cli.py parse --type KYI --date 2026-04-05
python cli.py parse --all  # data/raw/ 内の全ファイル

# 学習
python cli.py train --date-range 2020-01-01 2025-12-31 --time-limit 1800

# 予測
python cli.py predict --date 2026-04-05
python cli.py predict --date 2026-04-05 --race 11  # 特定レースのみ

# 回収率評価
python cli.py evaluate --date-range 2025-01-01 2025-12-31 --strategy fukusho_top3
```

---

## 10. 設定 (`config/settings.py`)

```python
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # JRDB
    jrdb_user: str = ""
    jrdb_pass: str = ""
    jrdb_base_url: str = "http://www.jrdb.com/member/datazip/"

    # Paths
    project_root: Path = Path(__file__).parent.parent
    data_raw_dir: Path = project_root / "data" / "raw"
    data_processed_dir: Path = project_root / "data" / "processed"

    # Modal
    modal_app_name: str = "boonta-ml"
    modal_volume_name: str = "boonta-models"
    model_name: str = "jrdb_predictor"

    # Training
    autogluon_time_limit: int = 1800
    autogluon_presets: str = "best_quality"

    model_config = {"env_file": ".env", "env_prefix": ""}
```

---

## 11. テスト戦略

### テスト構成

| テスト | 対象 | 方法 |
|--------|------|------|
| パーサー | spec.py, engine.py, kyi/sed/hjc.py | 実JRDBレコードバイナリでフィールド値検証 |
| フィーチャー | engineering.py, derived.py | サンプルDataFrameで変換結果検証 |
| モデル | functions.py (前処理部分) | AutoGluonをモック、前処理ロジックのみ検証 |
| 展開予想 | tenkai.py | モック予測結果からフォーマット出力検証 |
| ROI | roi.py | 既知の予測+HJCでROI計算検証 |

### テストフィクスチャ

`tests/fixtures/` に最小限のバイナリデータを配置:
- `kyi_sample.bin` — KYIレコード1-2件 (1024バイト/件)
- `sed_sample.bin` — 対応するSEDレコード
- `hjc_sample.bin` — 対応するHJCレコード

---

## 12. 依存関係 (`pyproject.toml`)

```toml
[project]
name = "boonta"
version = "2.0.0"
requires-python = ">=3.10"

dependencies = [
    "pandas>=2.0.0",
    "numpy>=1.24.0",
    "modal>=0.66.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
    "httpx>=0.25.0",
    "click>=8.0.0",
    "lhafile>=0.3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]

[project.scripts]
boonta = "cli:cli"
```

---

## 13. .gitignore

```
data/
notebooks/
.env
*.lzh
*.zip
*.csv
models/
__pycache__/
*.pyc
.venv/
.mypy_cache/
.pytest_cache/
.ruff_cache/
.modal/
*.egg-info/
dist/
build/
.DS_Store
```

---

## 14. 実装フェーズ

### Phase 0: プロジェクトセットアップ
1. 現在のmainに `v1.0.0` タグ
2. v1ファイル削除 (backend/, frontend/, docker-compose.yml)
3. v2ディレクトリ構成作成
4. pyproject.toml, .gitignore, config/settings.py 作成
5. CLAUDE.md (v2用) 作成

### Phase 1: パーサー
1. src/parser/spec.py — FieldSpec + 型変換
2. src/parser/engine.py — parse_record / parse_file
3. src/parser/kyi.py — KYI全フィールド定義
4. src/parser/sed.py — SED全フィールド定義
5. src/parser/hjc.py — HJC全フィールド定義 (繰り返し構造対応)
6. パーサーテスト

### Phase 2: ダウンローダー
1. src/download/jrdb.py — HTTP認証 + ZIP/LZH解凍 (HJCはlzhのみ、`lhafile`使用)
2. ダウンローダーテスト

### Phase 3: フィーチャーエンジニアリング
1. src/features/columns.py — カラム定義
2. src/features/engineering.py — 学習/予測用フィーチャー構築
3. src/features/derived.py — 派生フィーチャー
4. フィーチャーテスト

### Phase 4: Modal統合
1. src/model/image.py — Modal Image定義
2. src/model/functions.py — v1からJRDGフィーチャー対応に改修
3. src/model/client.py — 同期ModalClient
4. Modal deploy + 動作確認

### Phase 5: CLI + 予測パイプライン
1. cli.py — download/parse/train/predict コマンド
2. src/predict/runner.py — 予測オーケストレーター
3. src/predict/tenkai.py — 展開予想フォーマッター
4. E2E動作確認

### Phase 6: 回収率評価
1. src/predict/roi.py — HJC払戻ベースROI計算
2. evaluate CLIコマンド
3. バックテスト実行

### Phase 7: 仕上げ
1. 全テストパス
2. README.md 更新
3. CLAUDE.md 完成
4. `v2.0.0` タグ
