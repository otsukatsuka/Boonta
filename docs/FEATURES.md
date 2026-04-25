# 特徴量設計

ML モデル（is_place 予測）が使う特徴量の設計と一覧。

## 設計方針

1. **学習時のフィーチャーは KYI 由来のみ**。予測時に利用可能なデータに限定する。
2. **SED は補助役**。ラベル `is_place = (着順 <= 3)` の生成と、異常区分 `!= 0`（取消・失格）レコードの除外に使う。
3. **派生フィーチャー** で組合せ情報を明示化（速度バランス、位置取り変化など）。
4. **デフォルト値** は `src/model/functions.py` 内の前処理に定義（Modal 自己完結のため）。

将来的に同一馬の過去 SED 実績をルックバック特徴量として追加する余地はあるが、現状は未実装。

---

## 全 6 カテゴリ・~35 特徴量

### カテゴリ 1: 展開コア（KYI 由来）

JRDB が提供する展開予想データそのもの。

| 特徴量名 | 型 | 説明 |
|---------|-----|------|
| `pace_forecast` | categorical | ペース予想（H = ハイ、M = ミドル、S = スロー） |
| `mid_position` | numeric | 道中順位 |
| `mid_gap` | numeric | 道中差（0.1 秒単位） |
| `mid_position_io` | numeric | 道中内外（2: 内 〜 5: 大外） |
| `late3f_position` | numeric | 後 3F 順位 |
| `late3f_gap` | numeric | 後 3F 差（0.1 秒単位） |
| `late3f_io` | numeric | 後 3F 内外（2: 内 〜 5: 大外） |
| `goal_position` | numeric | ゴール順位 |
| `goal_gap` | numeric | ゴール差（0.1 秒単位） |
| `goal_io` | numeric | ゴール内外（1: 最内 〜 5: 大外） |
| `tenkai_symbol` | categorical | 展開記号コード |

### カテゴリ 2: スピード指標（KYI 予想値）

| 特徴量名 | 型 | 説明 |
|---------|-----|------|
| `ten_index` | float | テン指数（前半速度） |
| `pace_index` | float | ペース指数（中間） |
| `agari_index` | float | 上がり指数（終盤速度） |
| `position_index` | float | 位置指数 |
| `idm` | float | IDM（総合指数） |

### カテゴリ 3: 馬・厩舎・騎手指数（KYI 由来）

| 特徴量名 | 型 | 説明 |
|---------|-----|------|
| `jockey_index` | float | 騎手指数 |
| `info_index` | float | 情報指数 |
| `overall_index` | float | 総合指数 |
| `training_index` | float | 調教指数 |
| `stable_index` | float | 厩舎指数 |

### カテゴリ 4: 適性・リスク（KYI 由来）

| 特徴量名 | 型 | 説明 |
|---------|-----|------|
| `running_style` | categorical | 脚質（1: 逃げ 〜 4: 追込 等） |
| `distance_aptitude` | categorical | 距離適性 |
| `heavy_track_code` | categorical | 重適正コード（重馬場適性） |
| `start_index` | float | 馬スタート指数 |
| `gate_miss_rate` | float | 馬出遅率（%） |
| `upset_index` | numeric | 万券指数（穴馬指標） |

> **データ補足**: 2020 年データでは `upset_index`（万券指数）が全 NULL のためデフォルト値（50.0）で充填される。2025 年以降は値あり（JRDB 仕様変更）。

### カテゴリ 5: レース条件

| 特徴量名 | 型 | 説明 |
|---------|-----|------|
| `horse_number` | numeric | 馬番 |
| `waku` | numeric | 枠番 |
| `odds` | float | 基準オッズ |
| `popularity` | numeric | 基準人気順位 |
| `weight_carried` | float | 負担重量（kg） |

### カテゴリ 6: 派生フィーチャー（計算）

`src/features/derived.py` で生成。

| 特徴量名 | 計算式 | 意味 |
|---------|-------|------|
| `speed_balance` | `ten_index - agari_index` | 正 = 前傾、負 = 差し型 |
| `position_delta` | `goal_position - mid_position` | 負 = 追い上げ、正 = 後退 |
| `io_shift` | `goal_io - mid_position_io` | 内外移動量 |
| `log_odds` | `log(odds)` | オッズの対数（人気スケール圧縮） |
| `risk_score` | `gate_miss_rate × (1 - start_index/10)` | 出遅れリスク |
| `race_head_count` | レース内 KYI レコード数 | 出走頭数 |

---

## 学習データ構築（`build_training_features`）

```python
def build_training_features(kyi_df: pd.DataFrame, sed_df: pd.DataFrame) -> pd.DataFrame:
    """KYI（前日予想）と SED（実績）を race_key + 馬番 で JOIN。"""
    # 1. 両方に race_key カラムを構築
    # 2. race_key + 馬番 で merge
    # 3. is_place = (着順 <= 3) をラベルとして追加
    # 4. 異常区分 != 0 のレコードを除外（取消・失格等）
    # 5. 派生フィーチャー追加
    # 6. FEATURE_COLUMNS + "is_place" のみ返す
```

---

## 予測データ構築（`build_prediction_features`）

```python
def build_prediction_features(kyi_df: pd.DataFrame) -> pd.DataFrame:
    """KYI のみから推論用 DataFrame を生成。"""
    # 1. race_key を構築
    # 2. KYI 由来カラムから特徴量列を抽出
    # 3. 派生フィーチャー計算
    # 4. meta 列（horse_name, fukusho_odds など）を保持
    #    → ML には渡さないが、表示・EV 計算で使う
```

`fukusho_odds`（基準複勝オッズ）は ML には入れず、`predict.runner` 側で EV 計算に使う。

---

## 前処理（Modal `functions.py` 内、推論時に適用）

カテゴリカル列と数値列のデフォルト値を Modal 関数内にインラインで定義:

```python
categorical_cols = [
    "pace_forecast", "running_style", "distance_aptitude",
    "heavy_track_code", "tenkai_symbol",
]
numerical_defaults = {
    "idm": 50.0, "jockey_index": 50.0, "overall_index": 50.0,
    "ten_index": 50.0, "pace_index": 50.0, "agari_index": 50.0,
    "position_index": 50.0, "training_index": 50.0, "stable_index": 50.0,
    "info_index": 50.0,
    "odds": 10.0, "popularity": 8,
    "horse_number": 5, "waku": 4, "weight_carried": 55.0,
    "mid_position": 8, "late3f_position": 8, "goal_position": 8,
    "mid_gap": 5, "late3f_gap": 5, "goal_gap": 5,
    "mid_position_io": 3, "late3f_io": 3, "goal_io": 3,
    "start_index": 50.0, "gate_miss_rate": 5.0, "upset_index": 50,
}
```

NaN は上記デフォルトで充填。型は推定後にキャスト。

---

## 関連ドキュメント

- 全体アーキテクチャ: [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- ROI / EV 戦略: [docs/EVALUATION.md](EVALUATION.md)
- Modal 関数仕様: [docs/MODAL.md](MODAL.md)
