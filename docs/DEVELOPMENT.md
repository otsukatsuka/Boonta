# 開発ガイド

開発・テスト・コーディング規約・運用ルールをまとめたドキュメント。

## 開発フロー

### ブランチ運用

`main` への直接コミット運用（個人プロジェクト）。コミット粒度を意識し、論理単位で分けること。

> **データセキュリティ最優先**:
> - `data/`、`models/`、`.env`、`*.csv`、`*.lzh`、`*.zip`、`*_doc_utf8.txt`、`docs/private/` は **絶対にコミットしない**
> - `.gitignore` を変更したら必ず `git status` で確認
> - JRDB 由来のデータ・公式仕様書は会員規約上公開禁止

### コミットメッセージ

実例:

```
feat: add EV-based betting recommendations (ROI-focused)
fix: include horse_number in features sent to Modal predict
docs: add backtest handover for EV strategy validation
```

形式: `<type>: <summary>` — `feat`, `fix`, `docs`, `refactor`, `test`, `chore` など。

---

## テスト

### 実行

```bash
source .venv/bin/activate

pytest                              # 全テスト
pytest tests/test_parser/ -v        # パーサーテスト
pytest tests/test_features/ -v      # フィーチャーテスト
pytest -k "test_name" -v            # 名前マッチ
pytest --cov=src --cov-report=html  # カバレッジ HTML
```

### 構成

```
tests/
├── conftest.py
├── fixtures/           # JRDB レコードバイナリ等のフィクスチャ
├── test_parser/        # パーサー単体テスト
├── test_features/      # フィーチャーエンジニアリングテスト
├── test_model/         # Modal 前処理テスト（AutoGluon モック）
├── test_predict/       # 予測ランナー、展開予想、ROI、EV 買い目テスト
├── test_download/      # ダウンローダーテスト
└── test_cli.py         # CLI 統合テスト
```

### 方針

- 実 JRDB データを **テストでは使わない**（再現性・コミットセキュリティ）
- パーサーは仕様準拠のダミーレコード or 辞書ベースで検証
- Modal / AutoGluon は **モック**（実環境呼び出しは E2E 検証時のみ）

---

## 品質チェック

```bash
ruff check src/ cli.py config/
mypy src/ cli.py config/
```

### 設定

| ツール | ルール |
|--------|------|
| `ruff` | line-length 100、target Python 3.10 |
| `mypy` | Python 3.10、strict return type warnings |

CI（GitHub Actions）で `lint` / `test` ワークフローが走る（`.github/workflows/`）。

---

## コーディング規約

### 一般

- 行長 100 文字以内
- 型ヒント必須（特に関数のシグネチャ）
- docstring は最小限。1 行 docstring 推奨。多段落 docstring は禁止
- コメントは「なぜ」を書く。「何をしているか」は識別子で表現

### 設計ルール

#### ML フィーチャー

- 学習時のフィーチャーは **KYI 由来のみ**（予測時にも利用可能なデータに限定）
- SED はラベル（`is_place`）と異常区分フィルタにのみ使用
- 派生フィーチャーは `src/features/derived.py` に集約

#### Modal 関数

- `src/model/functions.py` は **自己完結**（`src/` 内の他モジュールから import しない）
- 前処理ロジックは `functions.py` 内にインライン定義（Modal 関数の制約）

#### AutoGluon

- preset は `best_quality` のみ。`extreme` は **禁止**（過学習・コスト過大）
- `eval_metric=roc_auc`、`problem_type=binary`、`label=is_place`

### Python バージョン

| 場所 | バージョン |
|------|----------|
| ローカル開発 | Python 3.10（venv） |
| Modal Image | Python 3.11（AutoGluon 1.4.0 互換） |

> **既知の workaround**: AutoGluon 1.4.0/1.5.0 の `TabularPredictor.load()` で `metadata_init["py_version"]` が欠落するバグがある。`require_py_version_match=False` で回避済み。詳細は [docs/MODAL.md](MODAL.md) を参照。

---

## ディレクトリ追加時の留意

新規モジュールを追加する場合、以下を確認:

1. `src/__init__.py` 等の更新
2. テスト追加（`tests/test_<module>/`）
3. `docs/ARCHITECTURE.md` のモジュール責務表に追記
4. 必要なら `cli.py` のサブコマンド追加

---

## 関連ドキュメント

- セットアップ: [docs/SETUP.md](SETUP.md)
- アーキテクチャ: [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- Modal 運用: [docs/MODAL.md](MODAL.md)
