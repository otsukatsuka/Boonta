---
name: predict-race
description: |
  Boonta v2 で JRDB レース予想を実行する。「{レース名}の予想して」「明日の{レース名}予想」「フローラSの予想お願い」のような自然発話で起動。
  ユーザーから日付＋レース名を受け、KYI ダウンロード→パース→predict CLI 実行→EV>1.2 の買い目（単勝＋3連複軸1頭流し）と展開コメントを ROI 重視の方針で提示する。
  TRIGGER: ユーザー発話に「予想」「買い目」「{重賞名/レース名}」が含まれ、Boonta プロジェクトディレクトリ配下で動作している場合。
---

# Boonta v2 レース予想 SKILL

JRDB データに基づくレース予想を、`feedback_betting_policy.md`（ROI 優先）と `project_backtest_handover.md`（EV>1.2 戦略の実証 ROI）に従って実行する。

## 必須前提

- 作業ディレクトリは `/Users/s.otsuka/Projects/Boonta`。それ以外なら起動しない。
- venv (`source .venv/bin/activate`) が有効。pip3 ベース、Python 3.10。
- JRDB 認証情報が `.env` にある（KYIダウンロードに必要）。

## ステップ

### 1. 入力解釈

ユーザー発話から **日付** と **レース名** を抜き出す:

- レース名: 「フローラS」「皐月賞」「東京11R」など。重賞名 or 場名+R番号。
- 日付:
  - 「今日」「明日」「今週末」「土曜」「日曜」などの相対表現は **今日（`date '+%Y-%m-%d'` または currentDate）を起点に YYMMDD へ正規化**。
  - 「明日」= currentDate +1日。「土曜」= 今週土曜（過ぎていれば翌週）。
  - 日付が不明・曖昧なら `AskUserQuestion` で確認（推測しない）。

YYMMDD は2桁年（例: 2026-04-26 → `260426`）。

### 2. KYIダウンロード＆パース

```bash
source .venv/bin/activate
# KYI 取得（既にあればスキップ）
test -f data/raw/KYI{YYMMDD}.txt || python cli.py download --type KYI --date {YYMMDD}
# パース（既にあればスキップ）
test -f data/processed/kyi_{YYMMDD}.csv || python cli.py parse --type KYI --date {YYMMDD}
```

**JRDB URL 仕様**: 2025年以降は `Kyi/20YY/KYI{YYMMDD}.zip` の年サブディレクトリ。downloader はフォールバック実装済み（`src/download/jrdb.py:_build_url`）。

**ダウンロード失敗時 (404)**: KYI未公開の可能性。ユーザーに「JRDB公開待ち」と通知して中断。

### 3. レース特定

KYI には **レース名カラムがない**（KYI=競走馬データのため）。場コード+R番号で特定する。

**JRDB 場コード**:
| コード | 場 |
|---|---|
| 01 | 札幌 |
| 02 | 函館 |
| 03 | 福島 |
| 04 | 新潟 |
| 05 | 東京 |
| 06 | 中山 |
| 07 | 中京 |
| 08 | 京都 |
| 09 | 阪神 |
| 10 | 小倉 |

CSV カラム `場コード` は CSV化時に先頭ゼロが落ちる（例: `'5'`、`'05'` ではない）。フィルタは `df['場コード'] == '5'` で。

**重賞→場/Rの推定**:
- 普通の重賞・特別はメイン (11R) 開催が多い
- 確信が持てなければユーザーに確認:
  ```
  「フローラSは東京11R想定で進めていいですか？」
  ```
- 出走馬を確認: `data/processed/kyi_{YYMMDD}.csv` を場コード+Rで絞って馬名一覧を出し、ユーザーに見せて齟齬がないか確認。

### 4. 予想実行

```bash
python cli.py predict --date {YYMMDD} --race {R} --ev-threshold 1.2
```

- `--race {R}` は **全場の同R番号** を出力する。出力には `【{場名} {R}R】 race_key=...` ヘッダが付くので（runner.py に追加済み）、当該レースのブロックだけを正規表現で抽出する。
  ```python
  import re
  m = re.search(r'【{venue} {R}R】.*?(?=\n【|\Z)', text, re.DOTALL)
  block = m.group(0) if m else text
  ```

### 5. 出力整形（ROI 優先 + 人間味コメント）

セクション構成:

#### 🏇 {レース名} / {YYYY-MM-DD} {場} {R}R
- **展開**: ペース予想・有利脚質・要注意の出遅率を1〜3行
- **ML TOP5**: 馬番・馬名・確率・単勝オッズ・人気（テーブル）
- **EVランキング**: 上位5頭（EV単・EV複の数値、★は EV>1.0）
- **結論**:
  - **厳密運用 (EV>1.2)**: 該当ありなら買い目、なければ「見送り」明記
    - 単勝: `ev_tansho EV>1.2` 該当馬を 100〜300 円
    - 3連複軸1頭流し: `recommend_nagashi` の出力（軸＋相手5頭、10点×100円）
  - **緩めるなら (EV>1.0)**: EV単>1.0 該当馬を提示（参戦判断はユーザー）
- **見解**: 1〜3行
  - ML 確率と人気の乖離（オッズ妙味の根拠）
  - 出遅率・脚質・適性の懸念
  - 整合性で軸を1頭選ぶならどれか
- **注意書き** (毎回必ず添える):
  - `ev_tansho EV>1.2` ROI 96.3% (2025年 N=1,759)
  - `ev_sanrenpuku_nagashi EV>1.2` ROI 127.7% (N=64、サンプル小、過大評価注意)
  - 過去実績であり保証ではない

#### エッジケース
- **EV>1.2 該当ゼロ**: 「見送り推奨」と明記。緩めた EV>1.0 候補があれば併記。
- **`recommend_nagashi` 軸不在**: 3連複軸1頭流しはスキップ、馬連/3連複 BOX フォールバックを参考表示。
- **ML確率1位が出遅率高 (>50%)**: 見解で必ず指摘（人気と確率に対する織り込み不足を疑う）。
- **KYI 未取得 (404)**: 「JRDB 未公開、{YYMMDD} 当日もしくは前日夜に再実行してください」で中断。

### 6. 提示後

- 結果はユーザーに見せて終わり。`out/` への保存は不要（過去レース解析時のみ別タスク）。
- 「実際にいくら賭けるか」「複数買い目をどう組み合わせるか」はユーザー決定。SKILL は提案までに留める。

## 参照すべきメモリ・ドキュメント

毎回の予想実行前に以下を意識する（既に MEMORY.md からロード済みのはず）:

- `~/.claude/projects/-Users-s-otsuka-Projects-Boonta/memory/feedback_betting_policy.md` — ROI 優先方針、EV+ 軸＋ML本命抑え＋穴EV相手の3連複軸1頭流しが基本
- `~/.claude/projects/-Users-s-otsuka-Projects-Boonta/memory/project_backtest_handover.md` — 戦略 ROI 実績、EV閾値の根拠
- `docs/EVALUATION.md` — EV 定義 (EV単 = 確率/3 × 単勝、EV複 = 確率 × 複勝)、戦略一覧

## ユーザーの好み

- **ROI > 的中率**。当てに行くより妙味を取る。
- **EV>1.2 厳守 が基本**。緩める提案は併記してもいいが、デフォルトは厳守。
- **数字を盛らない**。バックテスト ROI を語る際は N とサンプル期間を必ず添える。
- **人気馬の弱点（出遅率・適性ミスマッチ）は積極的に指摘**。本命視を盲信しない。

## 既知の制約

- `--race` フラグは全場の同R番号を出力する。単一場フィルタは stdout パースで対応。
- KYI 公開は土曜or日曜の前日（金曜or土曜）夜が多いが、確実なタイミングはJRDB依存。
- このSKILLは Boonta CLI に依存するため、プロジェクトルート外では動作しない。
