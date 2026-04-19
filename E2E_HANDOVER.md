# E2E検証 引き継ぎ資料

更新日: 2026-04-12（前回: 2026-04-06）

## やろうとしていたこと

JRDB実データ（data/raw/ に1937ファイル）を使ったE2E検証。
パイプライン全体: パース → 特徴量 → Modal学習 → 予測 → ROI評価 を実データで通す。

## 完了済み

### Phase 0: バグ修正 ✅

1. **バックアップファイルのリネーム完了**
   - `data/raw/SED220827bk.txt` → `.txt.bak`
   - `data/raw/HJC240922old.txt` → `.txt.bak`
   - これらがglob `SED*.txt` / `HJC*.txt` にマッチして重複レコードを生む問題を解消

2. **date-rangeフィルタリングバグ修正完了** (`cli.py`) → **コミット済み `e031985`**
   - `train` と `evaluate` コマンドが `--date-range` 引数を無視して全ファイルをglobしていたバグ
   - `_filter_by_date_range()` ヘルパー関数を追加し、両コマンドで適用

3. **AutoGluonバージョン修正** (`src/model/functions.py`, `src/model/image.py`)
   - `autogluon.tabular[all]==1.5.1` → **`1.4.0`** (1.5.1は存在せず、1.5.0は`py_version` KeyErrorバグあり)
   - Python `3.12` → `3.11`

4. **`py_version` KeyError 修正** (`src/model/functions.py`)
   - AutoGluon 1.4.0/1.5.0ともに `TabularPredictor.load()` で `metadata_init["py_version"]` が欠落するバグ
   - `require_py_version_match=False` を `predict()` と `get_feature_importance()` の `load()` に追加して回避

5. **`horse_number` 除外バグ修正** (`src/predict/runner.py`, `cli.py`)
   - `runner.py` と `cli.py`(evaluate) で Modal predict に送る特徴量から `horse_number` を除外していたが、モデルは `horse_number` を学習に使っていたため予測エラー
   - 除外リストから `horse_number` を削除

6. **テスト全パス**: 141テスト pass

### Phase 1: パーサー検証 ✅

単一ファイルでKYI/SED/HJCすべて正常パース確認:
- `KYI200105.txt`: 367レコード, 127カラム → 馬名・IDM・オッズ等正常読み取り
- `SED200105.txt`: 367レコード, 81カラム → 着順 1-18, 異常区分 363/367正常
- `HJC200105.txt`: 24レコード(=24レース), 77カラム → 複勝払戻データ正常
- 2025年データ(251228)も同様に正常

**特徴量エンジニアリング検証 ✅**
- KYI+SEDからbuild_training_features: 367→363サンプル（4件異常除外）
- 38カラム（35特徴量 + is_place + 派生等）
- is_place分布: 0=291(80.2%), 1=72(19.8%) → 妥当
- NULLゼロ（前処理で正しくデフォルト値充填）
- 注意: 2020年データは`万券指数`(upset_index)が全NULL→デフォルト50.0。2025年では正常に値あり（JRDB仕様変更）

### Phase 2: 一括パース ✅

`python cli.py parse --all` 完了、エラーなし:
- `data/processed/kyi.csv`: 286,060レコード, 127カラム
- `data/processed/sed.csv`: 286,060レコード, 81カラム
- `data/processed/hjc.csv`: 20,733レコード, 77カラム

### Phase 3: Modal デプロイ＆学習 ✅

1. `modal deploy` 成功 (Python 3.11 + AutoGluon 1.4.0)
2. 小規模学習(2025年1月, 3595サンプル, time_limit=300s) 成功
   - ROC-AUC: 0.808
   - 最良モデル: WeightedEnsemble_L3

### Phase 4: 予測パイプライン ✅

- `predict --no-ml` ✅: 展開予想の表示正常動作確認済み
- `predict (ML付き)` ✅: `require_py_version_match=False` + `horse_number` 修正で解決
  ```bash
  python cli.py predict --date 251228 --race 1  # 動作確認済み
  python cli.py predict --date 260412 --race 11 # 桜花賞予測実施
  ```

### Phase 5: ROI評価（小規模モデル） ✅

小規模モデル（2025-01学習）で2025-01を評価（パイプライン検証用、学習/評価データ重複のため参考値）:

| 戦略 | レース数 | 投資額 | 回収額 | 回収率 | 的中数 |
|------|---------|--------|--------|--------|--------|
| fukusho_top3 | 240 | 72,000円 | 56,920円 | 79.1% | 349 |
| umaren_top2 | 240 | 24,000円 | 17,770円 | 74.0% | 31 |
| sanrenpuku_top3 | 240 | 24,000円 | 14,150円 | 59.0% | 18 |

### Phase 6: 本番学習（2020-2024） ✅

`client.train_async()` で非同期投入、完了確認済み:
- **236,217サンプル** (536 KYI/SED files, 2020-01 〜 2024-12)
- time_limit=1800, presets=best_quality
- ROC-AUC: **0.805**
- 最良モデル: WeightedEnsemble_L3
- call_id: `fc-01KNYXAQ23GZCMRV6G1Z50MWYG` (完了済み)

### Phase 7: 本番評価 ⚠️ 未実施

## 次回やるべきこと

### 1. 本番ROI評価（最優先）

本番モデル（2020-2024学習）で2025年ホールドアウトデータを評価:

```bash
python cli.py evaluate --date-range 20250101 20251228 --strategy fukusho_top3
python cli.py evaluate --date-range 20250101 20251228 --strategy umaren_top2
python cli.py evaluate --date-range 20250101 20251228 --strategy sanrenpuku_top3
```

各戦略5〜15分かかる（レースごとにModal予測を呼ぶため）。

### 2. コードクリーンアップ＆コミット

`src/model/functions.py` にデバッグ用コードが残っている。削除してからコミット:
- `test_predict` エントリポイント（削除）
- `debug_model` エントリポイント + `_debug_model` 関数（削除）
- predict関数のtraceback付きエラー返却 → tracebackキーを削除

コミット対象:

| ファイル | 変更内容 | 状態 |
|---------|---------|------|
| `cli.py` | evaluate内の `horse_number` 除外バグ修正 | 未コミット |
| `src/model/functions.py` | AG 1.4.0, Python 3.11, `require_py_version_match=False`, traceback追加 | 未コミット（要クリーンアップ） |
| `src/model/image.py` | AG 1.4.0, Python 3.11 | 未コミット |
| `src/predict/runner.py` | `horse_number` 除外バグ修正 | 未コミット |
| `CLAUDE.md` L139 | `Python 3.12 + AutoGluon 1.5.1` → `Python 3.11 + AutoGluon 1.4.0` に更新 | 未変更 |

### 3. FutureWarning対応（任意）

`pd.concat` で空カラムの警告が出る。pandas将来バージョンで動作が変わる可能性。低優先度。

## 解決済みの問題

### `py_version` KeyError
- AutoGluon 1.5.0/1.4.0の `TabularPredictor.load()` で `metadata_init["py_version"]` が存在しないバグ
- `require_py_version_match=False` で回避。train/predictとも正常動作確認済み
- AutoGluon側のバグであり、バージョンを変えても同じ。将来バージョンで修正される可能性

### `horse_number` 除外バグ
- `runner.py` と `cli.py` (evaluate) で predict に渡す特徴量から `horse_number` を除外していた
- モデルは `horse_number` を含めて学習していたため、predict時に missing column エラー
- 除外リストから `horse_number` を削除して解決

### 当日KYIデータのレコード長
- JRDBからダウンロードした当日版KYI（`KYI260412.txt`）はレコード長1024（通常は1026）
- パーサーの `KYI_RECORD_LENGTH` デフォルトは1024なので問題なくパースできた
- ファイルはCP932エンコード。UTF8変換されたファイルはレコード長が変わるので使用不可

## 変更ファイル一覧

| ファイル | 変更内容 | Git状態 |
|---------|---------|---------|
| `cli.py` | `_filter_by_date_range()` 追加 | コミット済み `e031985` |
| `cli.py` | evaluate内 `horse_number` 除外修正 | 未コミット |
| `src/model/functions.py` | AG 1.4.0, Python 3.11, `require_py_version_match=False`, デバッグコード | 未コミット |
| `src/model/image.py` | AG 1.4.0, Python 3.11 | 未コミット |
| `src/predict/runner.py` | `horse_number` 除外修正 | 未コミット |
| `data/raw/SED220827bk.txt.bak` | リネーム（元 .txt） | gitignore対象 |
| `data/raw/HJC240922old.txt.bak` | リネーム（元 .txt） | gitignore対象 |
| `data/processed/*.csv` | parse --all で生成 | gitignore対象 |
| `data/raw/KYI260412.txt` | 当日KYIデータ（桜花賞予測で使用） | gitignore対象 |

## Modalの状態

- App: `boonta-ml` デプロイ済み（Python 3.11 + AutoGluon 1.4.0）
- Volume `boonta-models` にモデル格納済み:
  - `jrdb_predictor`: 236,217サンプルで学習、ROC-AUC 0.805、WeightedEnsemble_L3
