# Modal 統合

Boonta v2 は機械学習の学習・推論を [Modal](https://modal.com/) のサーバレス GPU/CPU 環境で実行する。本ドキュメントは構成・関数仕様・運用 Tips をまとめる。

## 構成

| 項目 | 値 |
|------|-----|
| App 名 | `boonta-ml` |
| Volume | `boonta-models` |
| Model 名 | `jrdb_predictor` |
| Image | `debian_slim` + Python 3.11 + AutoGluon 1.4.0 |
| 実装 | `src/model/functions.py`（自己完結） |
| Image 定義 | `src/model/image.py` |
| Client | `src/model/client.py`（同期、CLI 用） |

App 名・Volume 名は `config/settings.py` で `Settings.modal_app_name` / `modal_volume_name` として管理。`.env` で上書き可能。

---

## 関数一覧

| 関数 | 用途 | リソース |
|------|------|---------|
| `train_model()` | AutoGluon 学習 | memory 8 GB, CPU 4.0, timeout 7200 秒 |
| `predict()` | `is_place` 確率推論 | memory 4 GB, timeout 60 秒 |
| `get_model_status()` | モデル存在確認・メタ情報取得 | timeout 30 秒 |
| `get_feature_importance()` | 特徴量重要度取得 | memory 4 GB, timeout 60 秒 |

### `train_model(training_data_csv, model_name, time_limit, presets)`

引数:
- `training_data_csv` (str): 学習データの CSV 文字列
- `model_name` (str): モデル名（デフォルト `jrdb_predictor`）
- `time_limit` (int): タイムリミット（秒、デフォルト 1800）
- `presets` (str): AutoGluon preset。**`best_quality` 必須**

戻り値（dict）:
```json
{
  "success": true,
  "best_score": 0.805,
  "best_model": "WeightedEnsemble_L3",
  "metadata": {...}
}
```

### `predict(features_json, model_name)`

引数:
- `features_json` (str): 特徴量 JSON 配列文字列（1 レース分）
- `model_name` (str): モデル名

戻り値:
```json
{
  "success": true,
  "predictions": [0.78, 0.65, 0.43, ...]
}
```

ロード時に `require_py_version_match=False` を渡す（後述の workaround）。

### `get_model_status(model_name)`

モデル名のディレクトリが Volume にあるかを確認。

### `get_feature_importance(model_name)`

学習済みモデルから permutation feature importance を取得。

---

## デプロイ

```bash
modal deploy src/model/functions.py
```

App `boonta-ml` がデプロイされ、4 関数が利用可能になる。

### 動作確認

```bash
modal run src/model/functions.py::test_status        # モデル状態確認
modal run src/model/functions.py::test_train         # ダミーデータで学習テスト
```

ローカル CLI から:

```bash
python -c "from src.model.client import ModalClient; print(ModalClient().get_status())"
```

---

## クライアント（`src/model/client.py`）

CLI から同期呼び出しする薄いラッパー。v1 は async（FastAPI 用）だったが、v2 は CLI 用に sync 化。

```python
class ModalClient:
    def train(self, csv_data: str, time_limit: int = 1800,
              presets: str = "best_quality") -> dict: ...

    def predict(self, features: list[dict]) -> dict: ...

    def get_status(self) -> dict: ...

    def get_feature_importance(self) -> dict: ...
```

内部では `modal.Function.from_name("boonta-ml", ...)` で関数を取得して `.remote()` で呼び出す。

---

## 既知の workaround

### AutoGluon 1.4.0/1.5.0: `py_version` KeyError

`TabularPredictor.load()` が `metadata_init["py_version"]` を参照するが、学習時にこのキーが書き出されないバグ。

**対処**: `predict()` と `get_feature_importance()` の `load()` 呼び出しに `require_py_version_match=False` を追加。

将来 AutoGluon が修正したら除去可能。

### バージョン固定

- AutoGluon `1.4.0` を使用（`1.5.1` は存在しない、`1.5.0` は同上のバグあり）
- Modal Image の Python は **`3.11`**（`3.12` は AutoGluon 互換性問題）

`pyproject.toml` ローカル側は Python 3.10 でも動作可（CLI のみのため）。

---

## 学習データの扱い

`train_model()` は CSV 文字列を引数で受け取る。Modal 関数の境界をまたぐので外部 import なし、CSV はインラインで `pd.read_csv(io.StringIO(csv_data))` でパース。

---

## 運用 Tips

### 非同期投入とジョブ追跡

長時間学習を投入する場合、`client.train_async()` で `call_id` を取得してデタッチ可能。完了確認は `modal call <call_id>` で。

### Volume の中身確認

```bash
modal volume ls boonta-models
modal volume get boonta-models /jrdb_predictor/<file>
```

### コスト

学習: 8 GB × CPU 4.0 × 30 分 = 約 USD $0.x オーダー（Modal の従量課金）。
推論: 4 GB × 60 秒 / レース。`evaluate` で年間 3,400 レースを評価すると数分〜十数分。

---

## 関連ドキュメント

- アーキテクチャ全体: [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- 特徴量設計: [docs/FEATURES.md](FEATURES.md)
- セットアップ: [docs/SETUP.md](SETUP.md)
