# EV戦略バックテスト 引き継ぎ資料

作成日: 2026-04-19

## このドキュメントの目的

EV-based betting 機能（2026-04-19 皐月賞で初戦万馬券的中）の**実力検証**と、そこから派生する未実装機能の実装。N=1の結果なので、2025年データで数百レース規模のROIを測って「運 or 実力」を判定する。

## 背景

### 直近の出来事（2026-04-19 皐月賞）

- 本番モデル（2020-2024学習、ROC-AUC 0.805）で皐月賞予測
- 新実装のEV-basedレコメンド:
  - EV複 > 1.0 は **15番リアライズシリウス** のみ
  - EV単 > 1.0 は **6, 9, 16, 15, 17**（中穴中心）
- ユーザーが実際に購入: 3連複 **15軸 → 4, 6, 9, 12, 16, 17** (200円×15点=3,000円)
- 結果: 着順 4/15/9 → **15-4-9 で的中**
- 配当 10,420円 × 2 = **20,840円** (ROI 695%, 万馬券)

つまり: EV上位の中穴+ML本命を混ぜたハイブリッド戦略の初戦が成功した。ただしN=1なので実力評価はまだ不可能。

### 現在の実装（コミット済み）

**`0d064ea` feat: EV-based betting recommendations** で以下が入った:

- `src/predict/betting.py` (新規)
  - `compute_expected_values(race_df, predictions)`: EV単=is_place/3×単勝, EV複=is_place×複勝
  - `recommend_bets(ev_df, ev_threshold)`: 単勝/複勝の閾値ピック、馬連BOX、3連複BOX
- `src/features/engineering.py`: `build_prediction_features` に `fukusho_odds` をmeta列として追加
- `src/predict/tenkai.py`: EVランキング表・買い目セクション追加、`_to_int` 安全変換ヘルパー
- `cli.py predict`: `--no-bet`, `--ev-threshold` フラグ追加
- テスト: `tests/test_predict/test_betting.py` + tenkai拡充 (150/150 pass)

### 環境

- venv: `.venv` (Python 3.10) — `source .venv/bin/activate` 必須, `pip3`
- Modal: App `boonta-ml` deployed (Python 3.11 + AutoGluon 1.4.0)
- Volume `boonta-models` にモデル `jrdb_predictor`（ROC-AUC 0.805, 236,217サンプル 2020-2024）
- データ: `data/raw/` にKYI/SED/HJC（2020〜2025+260412, 260419）完備。`data/processed/*.csv` パース済み

## 優先タスク

### 🎯 Task 1: EV戦略のROIバックテスト（最優先）

**目的**: 2025年データで EV閾値戦略のROIが既存戦略（fukusho_top3等）を上回るか確認。N=1の運を排除。

**やること**:

1. `src/predict/roi.py` にEV-based戦略を追加:
   - `ev_tansho`: EV単 > 閾値 の馬に単勝100円ずつベット
   - `ev_fukusho`: EV複 > 閾値 の馬に複勝100円ずつベット
   - `ev_sanrenpuku_nagashi`: EV複 > 閾値の馬を軸に、EV単TOP5を相手に3連複1頭流し（軸なしレースはスキップ）
2. `cli.py evaluate` の `--strategy` choices に上記を追加、`--ev-threshold` オプションも追加
3. `build_prediction_features` が返す `fukusho_odds` が `predictions_df` までフローするよう確認（現状 `evaluate` 内で使ってない）
4. 小規模テスト（1ヶ月）で動作確認 → 2025年通年で実行

**実行例**:

```bash
source .venv/bin/activate

# 既存戦略のベースライン（比較用）
python cli.py evaluate --date-range 20250101 20251228 --strategy fukusho_top3
python cli.py evaluate --date-range 20250101 20251228 --strategy umaren_top2
python cli.py evaluate --date-range 20250101 20251228 --strategy sanrenpuku_top3

# 新EV戦略
python cli.py evaluate --date-range 20250101 20251228 --strategy ev_tansho --ev-threshold 1.0
python cli.py evaluate --date-range 20250101 20251228 --strategy ev_fukusho --ev-threshold 1.0
python cli.py evaluate --date-range 20250101 20251228 --strategy ev_sanrenpuku_nagashi --ev-threshold 1.0
```

**判定基準**:
- ROI 100% 超えたら「実力」(長期回収率プラス)
- 80-100% なら「現実的」(控除率20-25%を考えれば良戦略)
- 60%未満なら「ロジック見直し」

**注意**:
- `evaluate` は各レースごとにModal `predict` を呼ぶため、2025年通年で5〜15分×戦略数かかる
- HJC（払戻データ）は2025年全日程 `data/raw/HJC25*.txt` に入っている
- 閾値の感度分析も面白い: `--ev-threshold 0.9`, `1.1`, `1.2` で結果比較

### Task 2: 3連複軸1頭流し戦略の実装

**目的**: ユーザーが皐月賞で実際に使った「EV軸 → ML+EV相手流し」戦略をコードに落とす。

**やること**:

1. `src/predict/betting.py` に追加:
   ```python
   def recommend_nagashi(
       ev_df: pd.DataFrame,
       axis_criteria: str = "ev_fuku",       # "ev_fuku" or "prob" (ML)
       axis_threshold: float = 1.0,
       partner_criteria: str = "ev_tan",
       max_partners: int = 5,
   ) -> dict:
       """軸1頭流し 買い目生成.
       Returns: {"axis": int|None, "partners": list[int], "combos": list[tuple]}"""
   ```
2. 軸なし（閾値クリア馬なし）のレースは `axis=None` を返す → 買わない判断
3. `tenkai.py::_format_bets` に「3連複軸1頭流し」行を追加
4. `recommend_bets` の出力辞書に統合 or 並列

**重要ポイント**: 皐月賞実績では「軸: EV複プラス馬、相手: ML本命2頭 + EV単中穴3頭」の混成が効いた。`partner_criteria` だけでなく相手ソースを複数混ぜられるようにすると実戦に近い。

### Task 3: 予測確率のキャリブレーション確認

**目的**: モデルが楽観/悲観どちらに歪んでいるか把握。EV計算の信頼性に直結。

**やること**:

1. 2025年データで全レース予測 → 実際の着順と突き合わせ
2. 予測is_place確率を10%刻みでbinし、各binの実際の3着以内率を集計
3. 表 or 簡易プロット（matplotlib）で確認
   - 理想: 対角線（予測確率 = 実的中率）
   - 楽観: 予測＞実績（EV単/複を割り引く必要あり）
   - 悲観: 予測＜実績（EVを過小評価している）

**場所**: ad-hocなので `scripts/calibration_check.py` を新規作成でOK。CLIに入れるほどのものではない。

## 重要ファイル

| ファイル | 役割 |
|---------|------|
| `cli.py:160` `evaluate` | ROI評価エントリポイント |
| `src/predict/roi.py` | 戦略ごとのROI計算ロジック |
| `src/predict/betting.py` | EV計算 + 買い目推薦（今回追加） |
| `src/predict/tenkai.py` | 出力フォーマッタ |
| `src/features/engineering.py::build_prediction_features` | 特徴量 + meta(fukusho_odds) |
| `src/model/client.py::ModalClient.predict` | Modal 同期predict |
| `tests/test_predict/test_roi.py` | ROI戦略のテスト |
| `tests/test_predict/test_betting.py` | EV/買い目のテスト |
| `data/raw/HJC25*.txt` | 2025年払戻データ |

## 既知の設計上の妥協

- **EV単の定義**: `is_place/3 × 単勝オッズ`。本来は単勝確率モデルが必要。今はざっくり近似。
- **オッズ**: KYIの `基準オッズ` は発表時点。最終オッズとは乖離あり。最終オッズの取得源は未検討。
- **複勝オッズ**: KYIの `基準複勝オッズ` は下限値（JRDB仕様）。EVはやや保守的に出る（悪くはない）。
- **馬連/3連複の真のEV**: 馬連・3連複の実オッズは未取得。現状BOXは「単勝EV上位Nの組み合わせ」で代用。

## 検証手順（end-to-end）

1. `source .venv/bin/activate && pytest` → 150件以上 pass
2. `ruff check src/ cli.py` → All checks passed
3. Task 1実装後、`python cli.py evaluate --date-range 20250101 20250131 --strategy ev_tansho` で1ヶ月動作確認
4. 通年実行、ベースライン3戦略と比較。結果をこのドキュメントに追記
5. Task 2実装後、`python cli.py predict --date 260419 --race 11` で皐月賞の出力に「3連複軸1頭流し」行が追加されることを確認

## やらないこと（スコープ外）

- 最終オッズ取得（netkeibaスクレイピング等）— データソース拡張は次フェーズ
- モデル再学習（現行ROC-AUC 0.805で十分、まずは運用検証）
- 三連単戦略（オッズ分散が大きすぎて現状のEV近似では不適）
