# アーキテクチャ

Boonta v2 のシステム設計、データパイプライン、各モジュールの責務をまとめたドキュメント。

## v1 → v2 主要変更点

| 項目 | v1 | v2 |
|------|----|----|
| データソース | netkeiba.com (HTML scraping) | JRDB（固定長テキスト） |
| アーキテクチャ | FastAPI + React + SQLite | Python CLI パイプライン |
| ML フィーチャー | 34 個（scraping 由来） | ~35 個（JRDB 指数ベース） |
| 展開予想 | ルールベース（`pace.py`） | JRDB 展開予想データ + ML |
| 実行環境 | Docker / ローカルサーバ | CLI + Modal.com |
| 回収率評価 | なし | HJC 払戻データから算出 |

### v1 から継承

- Modal.com インフラ（App `boonta-ml`、Volume `boonta-models`）
- AutoGluon 設定（binary classification、ROC-AUC、`best_quality` preset）
- Modal functions パターン（`train_model` / `predict` / `get_model_status` / `get_feature_importance`）
- 自己完結型 Modal 関数（外部 import なし、前処理インライン）

---

## ディレクトリ構成

```
boonta/
├── README.md                  # プロジェクト入口
├── CLAUDE.md                  # Claude Code 向け開発指示書
├── pyproject.toml             # 依存関係・プロジェクト設定
├── cli.py                     # CLI エントリーポイント (click)
├── .env.example               # 環境変数テンプレート
├── .env                       # JRDB_USER, JRDB_PASS（.gitignore）
├── config/
│   └── settings.py            # Pydantic BaseSettings
├── data/                      # JRDB ダウンロード/処理済みデータ（.gitignore）
│   ├── raw/                   #   生 JRDB ファイル
│   └── processed/             #   変換済み CSV
├── src/
│   ├── download/              # JRDB ダウンローダー
│   ├── parser/                # 固定長ファイルパーサー（KYI/SED/HJC）
│   ├── features/              # フィーチャーエンジニアリング
│   ├── model/                 # Modal 関数 + クライアント
│   └── predict/               # 予測ランナー、展開予想、ROI、買い目推薦
├── tests/                     # pytest テスト一式
└── docs/                      # ドキュメント
    └── private/               # JRDB 仕様書・ハンドオーバー（.gitignore）
```

### モジュール責務

| モジュール | 責務 |
|-----------|------|
| `src/download/jrdb.py` | JRDB HTTP 認証 + ZIP/LZH 解凍、日付範囲ダウンロード |
| `src/parser/spec.py` | `FieldSpec` 定義、JRDB 型変換ルール |
| `src/parser/engine.py` | 汎用固定長パーサーエンジン（CP932 → UTF-8） |
| `src/parser/{kyi,sed,hjc}.py` | 各ファイルのフィールド定義 |
| `src/features/columns.py` | 特徴量カラム定義・デフォルト値 |
| `src/features/derived.py` | 派生フィーチャー計算 |
| `src/features/engineering.py` | `build_training_features`, `build_prediction_features` |
| `src/model/functions.py` | Modal 関数（train, predict, status, feature importance） |
| `src/model/image.py` | Modal Image 定義（Python 3.11 + AutoGluon 1.4.0） |
| `src/model/client.py` | Modal 同期クライアント（CLI 用） |
| `src/predict/runner.py` | 予測オーケストレーター |
| `src/predict/tenkai.py` | 展開予想フォーマッター |
| `src/predict/roi.py` | 戦略別 ROI 評価 |
| `src/predict/betting.py` | EV 計算・買い目推薦 |

---

## データパイプライン全体図

```
┌──────────────┐    ┌──────────────┐    ┌──────────────────┐    ┌────────────┐
│ JRDB Server  │───>│ data/raw/    │───>│ data/processed/  │───>│ Features   │
│ (ZIP/LZH)    │    │ KYI*.txt     │    │ kyi.csv          │    │ DataFrame  │
│              │    │ SED*.txt     │    │ sed.csv          │    │            │
│              │    │ HJC*.txt     │    │ hjc.csv          │    │            │
└──────────────┘    └──────────────┘    └──────────────────┘    └─────┬──────┘
   download/            parser/              features/                │
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
                                │  展開予想 + EV    │
                                │  ROI Evaluation   │
                                └──────────────────┘
```

### 学習フロー

```
cli.py train --date-range YYYYMMDD YYYYMMDD
  → data/raw/ から KYI / SED ファイルを範囲フィルタ
  → parse_file() で DataFrame 化
  → build_training_features(kyi_df, sed_df)
      ├─ race_key + 馬番 で JOIN
      ├─ is_place = (着順 <= 3) をラベル付与
      ├─ 異常区分 != 0 のレコード除外
      └─ 派生フィーチャー追加
  → CSV 文字列化 → ModalClient.train() で送信
  → Modal 上で AutoGluon 学習
```

### 予測フロー

```
cli.py predict --date YYMMDD [--race N]
  → data/raw/KYI{date}.txt をパース
  → build_prediction_features(kyi_df)
      └─ KYI 由来の特徴量のみ生成（SED 不要）
  → race_key 単位で ModalClient.predict() を呼び出し
  → format_tenkai() で展開予想テキスト出力
  → EV 計算 + 買い目推薦（--no-bet で無効化）
```

### 評価フロー

```
cli.py evaluate --date-range YYYYMMDD YYYYMMDD --strategy <戦略>
  → 範囲内 KYI を全パース → 予測実行
  → 範囲内 HJC を全パース → race_key で結合
  → evaluate_roi(predictions_df, hjc_df, strategy)
  → 戦略別の投資額・回収額・ROI・的中数を出力
```

---

## パーサー設計（概念）

JRDB は CP932 エンコードの固定長レコード。

| ファイル | レコード長 | 用途 |
|---------|-----------|------|
| KYI（競走馬データ） | 1024 bytes | 当日の馬データ、JRDB 指数、展開予想 |
| SED（成績データ） | 376 bytes | レース結果、実績タイム・指数 |
| HJC（払戻データ） | 444 bytes | 払戻金（繰り返し構造を含む） |

### レースキー構造

```
場コード(2) + 年(2) + 回(1) + 日(1, hex) + R(2) = 8 文字
```

- KYI / SED: `race_key + 馬番` で JOIN（馬単位レコード）
- HJC: `race_key` のみ（レース単位レコード）

### `FieldSpec` データクラス

```python
@dataclass
class FieldSpec:
    name: str           # カラム名
    offset: int         # 1-based バイトオフセット（仕様書準拠）
    length: int         # バイト長
    field_type: str     # "numeric" | "text" | "decimal" | "hex"
    scale: int = 0      # 小数桁数
    signed: bool = False
    description: str = ""
```

各ファイルのフィールド定義は `src/parser/{kyi,sed,hjc}.py` に実装。

> **Note**: フィールド単位のオフセット仕様は JRDB 会員規約に基づき非公開（`docs/private/jrdb_specs/` に保管）。

---

## Modal 構成

| 項目 | 値 |
|------|-----|
| App 名 | `boonta-ml` |
| Volume | `boonta-models` |
| Model 名 | `jrdb_predictor` |
| Image | `debian_slim` + Python 3.11 + AutoGluon 1.4.0 |
| 学習リソース | memory 8 GB, CPU 4.0, timeout 7200 秒 |
| 推論リソース | memory 4 GB, timeout 60 秒 |

詳細は [docs/MODAL.md](MODAL.md) を参照。

---

## 出力フォーマット（展開予想）

```
══════════════════════════════════════════════
【展開予想】2026/04/05 阪神11R 大阪杯 (G1) 芝2000m
══════════════════════════════════════════════

■ ペース予想: ミドル (M)
  逃げ馬: 3番ドウデュース
  先行争い: 3番, 7番, 12番

■ 位置取り予想
  馬番  馬名            脚質  道中  後3F  ゴール  内外
    3  ドウデュース      逃げ    1     2      1    内
    7  リバティアイランド 先行    3     3      2    中
   ...

■ ML予測 (is_place 確率)
  1位:  3番 ドウデュース      78.2%
  2位:  7番 リバティアイランド 65.1%
   ...

■ EV ランキング / 推奨買い目
  EV単 > 1.0: 6, 9, 16
  EV複 > 1.0: 15
  3連複 BOX: ...

■ 有利馬・不利馬
  ★有利: 3番 (逃げ有利のミドルペース + 内枠)
  ▲不利: 5番 (出遅率 12.5%, スタート指数低)
```

| セクション | データソース | ロジック |
|-----------|------------|---------|
| ペース予想 | KYI ペース予想 | 各馬の H/M/S 分布から決定 |
| 位置取り | KYI 展開予想データ | 道中順位 / 後3F順位 / ゴール順位 |
| ML 予測 | Modal `predict()` | `is_place` 確率でランキング |
| EV / 買い目 | Modal 予測 + KYI オッズ | EV 単 = `is_place/3 × 単勝`、EV 複 = `is_place × 複勝` |
| 有利 / 不利 | KYI + 派生フィーチャー | 脚質 × ペース × 内外の組合せ判定 |

詳細は [docs/EVALUATION.md](EVALUATION.md) と [docs/FEATURES.md](FEATURES.md) を参照。
