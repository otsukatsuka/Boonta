---
name: analyze-race-roi
description: |
  Boonta v2 でレース後の ROI 分析を実行する。「今日のROI」「今週末の回収率」「先週土曜のROI見せて」「{日付}のレース結果と回収率」のような自然発話で起動。
  ユーザーから日付（単日 or 範囲）を受け、SED/HJC ダウンロード→パース→ingest→backtest run（ev_tansho EV>=1.30 を主、感度スイープ付き）を回し、戦略比較・個別レース内訳・注意書きを ROI 重視の方針で提示する。
  TRIGGER: ユーザー発話に「ROI」「回収率」「結果」「答え合わせ」「収支」「払戻」「賭けた結果」のいずれかが含まれ、Boonta プロジェクトディレクトリ配下で動作している場合。
---

# Boonta v2 レース後 ROI 分析 SKILL

JRDB SED/HJC データに基づくレース結果突合と ROI 計算を、`feedback_betting_policy.md`（ROI 優先）と `project_backtest_handover.md`（EV 戦略の実証 ROI）に従って実行する。`predict-race` の対になる「事後評価」スキル。

## 必須前提

- 作業ディレクトリは `/Users/s.otsuka/Projects/Boonta`。それ以外なら起動しない。
- venv (`source .venv/bin/activate`) が有効。pip3 ベース、Python 3.10。
- JRDB 認証情報が `.env` にある（SED/HJC ダウンロードに必要）。
- DB 初期化済み (`data/boonta.db` 存在)。未初期化なら `python cli.py db init`。

## ステップ

### 1. 入力解釈

ユーザー発話から **日付範囲** を抽出する:

- 単日表現: 「今日」「{月}/{日}」「先週土曜」 → `(D, D)` の同日範囲。
- 範囲表現: 「今週末」「先週末」「先月」「{D1}〜{D2}」 → `(start, end)`。
  - 「今週末」= 直近の (土, 日)。今日が日曜なら (土, 今日)。今日が月〜金なら **直近過去の** (土, 日)（ROI は事後評価なので未来日は不可）。
  - 「先週末」= 1 週前の (土, 日)。
- 相対表現は currentDate を起点に YYMMDD（CLI 用）と YYYYMMDD（backtest 用）の両方で正規化する。
- 曖昧・不明・未来日が含まれるなら `AskUserQuestion` で確認（推測しない）。例:
  - 「『今週末』は 2026-04-25 (土) 〜 2026-04-26 (日) でいいですか？」

YYMMDD は 2 桁年（例: 2026-04-26 → `260426`）。`backtest run --date-range` は YYYYMMDD（例: `20260426`）。

### 2. SED/HJC 存在チェック → ingest

範囲内の **各日について** SED と HJC が `data/raw/` にあるか確認:

```bash
source .venv/bin/activate
for d in 260426; do  # 範囲内の YYMMDD を列挙
  for t in SED HJC; do
    test -f data/raw/${t}${d}.txt && echo "  ${t}${d}: ok" || echo "  ${t}${d}: MISSING"
  done
done
```

不足分は **download → parse → db ingest** を順に実行:

```bash
# 例: SED260426 不足
python cli.py download --type SED --date 260426
python cli.py parse    --type SED --date 260426
python cli.py db ingest --type SED --date 260426
# HJC も同様
python cli.py download --type HJC --date 260426
python cli.py parse    --type HJC --date 260426
python cli.py db ingest --type HJC --date 260426
```

ショートカット（BAC+KYI+SED+HJC まとめて、不足は skip）:

```bash
python cli.py db ingest-all --date 260426
```

**ダウンロード失敗 (404)**: JRDB 未公開（典型: 当日夜だと SED/HJC のどちらかが未公開）。
- HJC のみ未公開 → ROI 計算不可。「{YYMMDD} HJC が JRDB 未公開のため ROI 算出不可、再実行をおすすめします（公開は通常レース当日深夜〜翌朝）」と通知して中断。
- SED のみ未公開 → 同様に中断（HJC は払戻、SED は着順、両方ないと整合できない）。
- 両方 OK → 続行。

**ingest 後の整合確認**:

```bash
sqlite3 data/boonta.db "
  SELECT COUNT(*) AS payouts
  FROM hjc_payout
  WHERE race_id IN (SELECT id FROM race WHERE held_on='2026-04-26');
"
```

`0` なら ingest 漏れ。`db ingest --type HJC --date YYMMDD` を再実行。

### 3. 予測 (Prediction テーブル) の有無を確認

backtest は **DB の `prediction` テーブル**を読む。`cli.py predict` は **stdout 出力のみで DB に書かない**（ファイル予測専用）。DB に Prediction を入れるのは以下のみ:

- Web UI から「予測する」ボタン (`POST /api/races/{race_key}/predict`)
- 一括 API (`POST /api/races/predict-batch` with `{"date": "YYYY-MM-DD"}`)

範囲内の各日について件数確認:

```bash
sqlite3 data/boonta.db "
  SELECT r.held_on, COUNT(DISTINCT r.id) AS races, COUNT(p.id) AS preds
  FROM race r
  LEFT JOIN horse_entry he ON he.race_id = r.id
  LEFT JOIN prediction p   ON p.horse_entry_id = he.id
  WHERE r.held_on BETWEEN '2026-04-26' AND '2026-04-26'
  GROUP BY r.held_on
  ORDER BY r.held_on;
"
```

**判定**:
- `preds = 0` の日が範囲内に 1 日でもある → **自動で予測は回さない**（Modal cost & 時間が大きい）。ユーザーに次のいずれかを促して中断:
  ```
  「{YYMMDD} は予測が DB 未投入です。次のどちらかをお願いします:
   (A) Web UI を開き ({serve URL}/?date={YYYY-MM-DD}) 「全レース予測 RUN」を実行
   (B) API サーバー起動中なら以下を実行:
       curl -X POST http://localhost:8000/api/races/predict-batch \
            -H 'Content-Type: application/json' \
            -d '{\"date\": \"{YYYY-MM-DD}\"}'
   完了後にこの SKILL を再実行してください。」
  ```
  サーバー起動コマンド: `python cli.py serve --no-vite --port 8000`
- `preds > 0` だが `races` の半分以下 → 部分予測の警告を出した上で続行可否をユーザーに確認。
- 全日 `preds > 0` 充足 → 続行。

### 4. backtest 実行（メイン）

デフォルト戦略は **`ev_tansho` EV>=1.30**（現状ベスト）。`backtest run` は感度スイープを内蔵しているので、`--no-sensitivity` を付けない限り EV 1.0/1.1/1.2/1.3/1.4 が `BacktestSensitivity` テーブルに記録される。

```bash
python cli.py backtest run \
  --strategy ev_tansho \
  --date-range 20260426 20260426 \
  --ev-threshold 1.30
```

**追加で広く見たい場合** (ユーザーが「全戦略比較見たい」と発話、もしくはサンプル少ない単日):

```bash
python cli.py backtest run \
  --strategy all \
  --date-range 20260426 20260426 \
  --ev-threshold 1.30
```

CLI 出力は短いサマリのみ。詳細は DB から取り出す。

**冪等性**: `(strategy, date_from, date_to, ev_threshold, model_version)` の UNIQUE 制約で UPSERT されるため、同日複数回実行しても DB は肥大化しない。

**失敗時**:
- `No predictions in DB` 系 → ステップ 3 に戻り予測投入。
- `No predictions or payouts in date range` → SED/HJC は ingest されたが Race と紐付いていない可能性。`sqlite3 data/boonta.db "SELECT COUNT(*) FROM hjc_payout WHERE race_id IN (SELECT id FROM race WHERE held_on='2026-04-26');"` で診断。0 ならステップ 2 の ingest 漏れを再点検。

### 5. 個別レース内訳の取得

`backtest_detail.bets > 0` のレースが「実際に賭けたレース」。EV>=1.30 該当馬がそのレースの単勝対象。

**重要な注意**: `horse_entry.goal_position` は JRDB ペース予想による **予想着順** であり、SED ingest で実着順に上書きされない（既知の設計ギャップ）。実着順・実払戻は HJC raw JSON (`単勝馬番_1`, `単勝払戻_1`) を参照する必要がある。SQLite の `json_extract` は HJC の unicode-escape 済みキーを上手く拾えない場合があるので、Python ORM 経由で取り出すのが確実:

```bash
source .venv/bin/activate && python3 -c "
from src.db.session import session_scope
from src.db.models import Race, HjcPayout, HorseEntry, Prediction
from sqlalchemy import select
from datetime import date

D_FROM, D_TO = date(2026,4,26), date(2026,4,26)
MV = 'jrdb_predictor@2026-04-11'   # latest_model_version() で動的に取ってもよい
EV = 1.30

with session_scope() as s:
    payouts = {rid: raw for rid, raw in s.execute(
        select(Race.id, HjcPayout.raw)
        .join(HjcPayout, HjcPayout.race_id == Race.id)
        .where(Race.held_on.between(D_FROM, D_TO))
    ).all()}
    bets = s.execute(
        select(Race.venue_code, Race.race_no, Race.id,
               HorseEntry.horse_number, HorseEntry.name,
               Prediction.prob, HorseEntry.odds, Prediction.ev_tan)
        .join(HorseEntry, HorseEntry.id == Prediction.horse_entry_id)
        .join(Race, Race.id == HorseEntry.race_id)
        .where(Race.held_on.between(D_FROM, D_TO))
        .where(Prediction.model_version == MV)
        .where(Prediction.ev_tan >= EV)
        .order_by(Race.venue_code, Race.race_no, Prediction.ev_tan.desc())
    ).all()

    venues = {'01':'札幌','02':'函館','03':'福島','04':'新潟','05':'東京','06':'中山','07':'中京','08':'京都','09':'阪神','10':'小倉'}
    total_bet = total_ret = hits = 0
    for v, rno, rid, num, name, prob, odds, ev in bets:
        raw = payouts.get(rid, {})
        try:
            win_n = int(raw.get('単勝馬番_1') or 0)
            pay = int(raw.get('単勝払戻_1') or 0)
        except (TypeError, ValueError):
            win_n, pay = 0, 0
        ret = pay if num == win_n else 0
        total_bet += 100; total_ret += ret
        if ret > 0: hits += 1
        outcome = f'◎ +{ret-100:>5,}円' if ret>0 else '×'
        print(f'{venues.get(v,v)} {rno:>2}R 馬{num:>2} {(name or \"\")[:14]:<14} prob={prob:.3f} odds={odds:>5.1f} EV={ev:>4.2f} 勝馬{win_n}/払戻{pay}円 {outcome}')
    pnl = total_ret - total_bet
    roi = (total_ret / total_bet * 100) if total_bet else 0
    print(f'合計: {len(bets)}ベット, {hits}的中, 投資{total_bet:,}円, 払戻{total_ret:,}円, 損益{pnl:+,}円, ROI{roi:.1f}%')
"
```

`MV` (model_version) は `latest_model_version()` で動的取得できる（runner.py 参照）が、当該日に複数 version 混在しないなら固定値で十分。

感度スイープ結果:

```bash
sqlite3 -header -column data/boonta.db "
  SELECT s.ev_threshold, s.bet_races, s.hits, s.roi
  FROM backtest_sensitivity s
  JOIN backtest_run br ON br.id = s.run_id
  WHERE br.strategy='ev_tansho'
    AND br.date_from='2026-04-26'
    AND br.date_to  ='2026-04-26'
  ORDER BY s.ev_threshold;
"
```

### 6. 出力整形

セクション構成:

#### 📊 ROI レポート / {YYYY-MM-DD} （範囲なら 〜 YYYY-MM-DD）

##### サマリ（メイン戦略: ev_tansho EV>=1.30）

| 指標 | 値 |
|---|---|
| 対象日数 | N 日 |
| 総レース数 | XX |
| 投票レース数 | XX |
| ベット総額 | XX,XXX 円 (= ベット数 × 100 円) |
| 払戻総額 | XX,XXX 円 |
| 損益 | ±XX,XXX 円 |
| **ROI** | **XXX.X%** |
| 的中数 | XX / XX |

##### 戦略比較（ev_tansho 主、感度スイープ）

| EV 閾値 | 投票数 | 的中 | ROI |
|---|---|---|---|
| 1.0 | … | … | … |
| 1.1 | … | … | … |
| 1.2 | … | … | … |
| **1.3** | **…** | **…** | **…** |
| 1.4 | … | … | … |

`--strategy all` を回した場合は他戦略も併記。

##### 個別レース内訳（賭けた全レース）

| 日付 | 場 | R | 馬番 | 馬名 | 確率 | 単オッズ | EV | 着順 | 払戻 | 損益 |
|---|---|---|---|---|---|---|---|---|---|---|
| ... |

場名は `venue_code` を `src/api/labels.py` で参照（01=札幌 / 02=函館 / 03=福島 / 04=新潟 / 05=東京 / 06=中山 / 07=中京 / 08=京都 / 09=阪神 / 10=小倉）。

##### TOP3 / WORST3

- **大当たり TOP3**: 損益降順で 3 行
- **取りこぼし WORST3**: 損益昇順で 3 行（外れ含む）

##### 注意書き（毎回必ず添える）

- メイン戦略 `ev_tansho EV>=1.30` の長期 ROI: **106%** (`project_backtest_handover.md` 2026-04-26 再検証, N=1,080)。
- 比較: `ev_tansho EV>=1.40` は ROI **151%** だが N が小さく分散大。
- `ev_fukusho` / 他 ML 戦略は全閾値帯で ROI<100%（実用は ev_tansho に絞る）。
- 当日/今回の ROI は **短期サンプル**。N が小さいほど分散が大きく、長期 ROI からの乖離は珍しくない。
- 過去実績であり保証ではない。

##### Web UI 案内

```
詳細は BACKTEST 画面でも参照できます: http://localhost:8000/backtest
（API サーバーを起動していない場合: python cli.py serve）
```

### 7. エッジケース

- **範囲内に当日（未開催）が含まれる**: 「{YYMMDD} は未来日です。範囲を {終了日まで} に縮めますか？」と確認。
- **HJC 公開遅延**: ステップ 2 で 404 → 中断＋再実行案内。
- **予測未投入**: ステップ 3 で警告＋手動投入案内（自動投入はしない）。
- **EV>=1.30 該当ゼロ（見送り日）**: サマリは「投票レース 0、ベット 0、ROI N/A（見送り日）」と明記。感度スイープも 0 行ばかりなら EV 閾値を下げた行（1.0〜1.2）に何があるか併記。
- **モデル version 切替直後**: backtest は最新 `model_version` を選ぶ。古い予測しかない日は backtest 失敗。`sqlite3 ... "SELECT DISTINCT model_version FROM prediction ORDER BY model_version;"` で一覧確認。
- **ingest 漏れ**: `cli.py db ingest-all` を再実行（idempotent）。

### 8. 後始末

- backtest 結果は `backtest_run` / `backtest_detail` / `backtest_sensitivity` に永続化済み（UPSERT）。再計算しても DB は肥大化しない。
- 結果は stdout 表示のみ。`docs/private/handover/` への記録はユーザー判断（個人賭け金は記録しない方針）。
- ユーザーが「memory に追記して」と明示した場合のみ `~/.claude/projects/-Users-s-otsuka-Projects-Boonta/memory/project_backtest_handover.md` に追記検討。

## 参照すべきメモリ・ドキュメント

毎回の ROI 分析実行前に以下を意識する（既に MEMORY.md からロード済みのはず）:

- `~/.claude/projects/-Users-s-otsuka-Projects-Boonta/memory/feedback_betting_policy.md` — ROI 優先方針。
- `~/.claude/projects/-Users-s-otsuka-Projects-Boonta/memory/project_backtest_handover.md` — 戦略 ROI 実績、EV 閾値の根拠（ev_tansho EV>=1.30 ROI 106% (N=1,080) 等）。
- `docs/EVALUATION.md` — EV 定義、戦略一覧、payoff 計算。

## ユーザーの好み

- **ROI > 的中率**。短期成績で一喜一憂せず長期 ROI を基準とする。
- **数字を盛らない**。N と期間を必ず添える。当日 ROI が長期ベンチマークを上回ったり下回ったりしても「サンプル小」を明記。
- **Public repo に機密データを出さない**。個人賭け金額・口座残高は ROI 計算で使わない（100 円固定基準）。
- **EV>=1.30 ev_tansho が現状ベスト**。比較対象として他戦略を併記してもよいが、推奨は ev_tansho 1.30 を中心に据える。

## 設計判断（覚書）

- **予測未投入は自動で回さない（手動）**: Modal を全レース呼ぶとコスト・時間が大きいので、SKILL は警告で止める。明示操作 (`predict-batch`) を待つ。
- **感度スイープはデフォルト ON**: `backtest run` 内蔵で追加コストほぼ無料、見送り日判定にも有用。重い時は `--no-sensitivity`。

## 既知の制約

- `cli.py predict` は DB に書かない（ファイル/stdout 専用）。DB Prediction 投入は API 経由のみ。
- HJC URL は `https + .zip`、SED URL は `http + .zip`（downloader はフォールバック実装済み）。
- 範囲内に複数 model_version の予測が混在する場合、backtest は最新 version で絞られるため古い version の予測は対象外になる。
- **`horse_entry.goal_position` は KYI の予想着順**で、SED ingest が実着順で上書きしない（既知の設計ギャップ、`src/db/ingest.py` の `ingest_sed` は race メタデータのみ backfill）。実着順・実払戻は HJC raw の `単勝馬番_1` / `単勝払戻_1` 等を参照する（ステップ 5 のスクリプト参照）。
- このSKILLは Boonta CLI と SQLite DB に依存するため、プロジェクトルート外では動作しない。
