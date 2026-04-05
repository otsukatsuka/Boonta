# Boonta Ver.2 要件定義

## プロジェクト概要

JRDBデータを使った競馬展開予想AIシステム。  
展開予想をコアバリューとして、AutoGluonベースのモデルでレース予測を行う。

---

## ディレクトリ構成

```
boonta/
├── CLAUDE.md              # Claude Code向け指示書
├── README.md
├── .gitignore             # data/ notebooks/ を必ず除外
├── config/
│   └── settings.py        # 設定値（環境変数参照）
├── data/
│   ├── raw/               # JRDBダウンロードファイル (.gitignore対象)
│   └── processed/         # 変換済みCSV (.gitignore対象)
├── src/
│   ├── download/          # JRDBダウンローダー
│   ├── parser/            # 固定長→CSV変換
│   ├── features/          # フィーチャーエンジニアリング
│   ├── model/             # AutoGluonモデル
│   └── predict/           # 予測・展開予想出力
├── tests/
└── notebooks/             # 分析用 (.gitignore対象)
```

---

## データパイプライン要件

### Step 1: ダウンロード

- JRDB会員情報は環境変数で管理（`JRDB_USER`, `JRDB_PASS`）
- 対象ファイル: `KYI`（前日データ）, `SED`（競走成績）, `HJC`（払戻）
- lzh解凍対応（`lhasa` コマンド or Pythonライブラリ）
- 開催日単位でダウンロード・管理

### Step 2: パーサー

- 固定長テキスト（CP932）→ UTF-8 CSV変換
- KYI: 1024 BYTE/レコード
- SED: 376 BYTE/レコード
- HJC: 444 BYTE/レコード
- レースキーをPKとして各ファイルをJOINできる設計

### Step 3: フィーチャーエンジニアリング

| フィーチャー | ソース | 用途 |
|---|---|---|
| ペース予想 (H/M/S) | KYI | 展開コア |
| 道中順位・道中差・道中内外 | KYI | 展開コア |
| 後3F差・後3F内外 | KYI | 展開コア |
| ゴール内外 | KYI | 展開コア |
| スタート指数 | KYI | 出遅れリスク |
| 重馬場適性コード | KYI | 馬場対応力 |
| テン指数・ペース指数・上がり指数 | KYI + SED | スピード指標 |
| 万券指数 | KYI | 穴馬フィルタ |
| コーナー通過順位1〜4（実績） | SED | 学習用ラベル |
| レースペース実績 (H/M/S) | SED | 学習用ラベル |
| 馬場差 | SED | 馬場補正 |
| 不利コード（前・中・後） | SED | ノイズ除去 |
| コース取り（最内〜大外） | SED | バイアス補正 |
| 払戻金額 | HJC | 回収率評価 |

---

## モデル要件

- **フレームワーク**: AutoGluon v1.5.1以上（既存Boontaからアップグレード）
  - TabPFN-2.5は非商用制限あり・Modal.com実績なしのため今回は見送り
  - AutoGluonは精度・商用利用・既存資産の継承すべてで優位
- **実行環境**: Modal.com（Intel Mac制約の回避）
- **既存資産の扱い**: ver.1のAutoGluon学習パイプライン・Modal.com設定は極力継承する。新規実装はパーサーとフィーチャー部分に限定すること
- **予測ターゲット**:
  - 展開予想（ペース・位置取り）
  - 着順予測
- **評価指標**: 回収率（HJCの払戻データで算出）

---

## 展開予想出力要件

Boontaの出力として以下を必ず含める。

- レース全体のペース予想（ハイ/ミドル/スロー）
- 各馬の予測位置取り（逃げ/先行/差し/追込）
- 有利馬・不利馬の明示
- 馬場状態を考慮したコメント

---

## Git運用方針

- **作業開始前に現状のmainに `v1.0.0` タグを打つこと**
- その後mainに直接破壊的変更を入れてver.2.0.0を作成する
- 一人プロジェクトなのでブランチ不要、Claude Codeは余計なブランチを切らないこと
- 完成時に `v2.0.0` タグを打つ

---

## セキュリティ・運用要件

### ⚠️ 絶対に守ること

- `data/raw/`, `data/processed/`, `notebooks/` は `.gitignore` で除外
- JRDBの生データ・変換済みCSVは**絶対にCommitしない**
- 認証情報（JRDB_USER, JRDB_PASS）は環境変数のみで管理、ハードコード禁止
- `.env` ファイルも `.gitignore` 対象

### .gitignore 必須設定

```
data/
notebooks/
.env
*.lzh
*.csv
models/
```

---

## CLAUDE.md 記載事項（Claude Code向け）

Claude Codeに必ず伝えること。

- データファイルは `data/` 配下のみ扱う
- 学習データのCommitは絶対禁止
- 環境変数は `.env` から読み込む（`python-dotenv`使用）
- パーサーは各ファイル仕様（KYI/SED/HJC）に忠実に実装する
- フィーチャー追加時は `features/` に集約し、モデルコードに直接書かない
- テストは `tests/` に必ず書く

---

## 実装フェーズ

### Phase 1: データ基盤（最優先）
1. `.gitignore` と `CLAUDE.md` の作成
2. JRDBダウンローダーの実装
3. KYI / SED / HJC パーサーの実装
4. 動作確認（今日の大阪杯データで検証）

### Phase 2: フィーチャー & モデル
1. フィーチャーエンジニアリング実装
2. AutoGluon学習パイプライン構築
3. Modal.com対応

### Phase 3: 展開予想出力
1. 予測結果の展開予想フォーマット出力
2. 回収率評価ロジック実装
3. 週次自動実行フロー整備
