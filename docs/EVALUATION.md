# 評価戦略 (ROI / EV)

過去レースで予測 → 払戻データ（HJC）と突き合わせて回収率（ROI）を測る仕組み。`cli.py evaluate` のロジックと各戦略の解説。

## 評価フロー

```
1. 指定期間の KYI を全パース
2. build_prediction_features() で特徴量を生成
3. race_key 単位で Modal predict() を呼び、is_place 確率を取得
4. 指定期間の HJC を全パース、race_key で結合
5. evaluate_roi(predictions_df, hjc_df, strategy) で戦略別 ROI を算出
```

実装: `src/predict/roi.py`、`src/predict/betting.py`。

## 戦略一覧

### ML ベース戦略（`is_place` 確率の上位を機械的に買う）

| 戦略 | 投資 | 説明 |
|------|------|------|
| `fukusho_top3` | 各 100 円 × 3 頭 = 300 円/レース | ML 予測上位 3 頭の複勝 |
| `umaren_top2` | 100 円 × 1 点 | 上位 2 頭の馬連 |
| `sanrenpuku_top3` | 100 円 × 1 点 | 上位 3 頭の 3 連複 |

### EV ベース戦略（期待値プラスの馬のみ買う）

| 戦略 | 投資 | 説明 |
|------|------|------|
| `ev_tansho` | 各 100 円 × 該当頭数 | EV 単 > 閾値の馬に単勝 |
| `ev_fukusho` | 各 100 円 × 該当頭数 | EV 複 > 閾値の馬に複勝 |
| `ev_sanrenpuku_nagashi` | 100 円 × N 点 | EV 複 > 閾値を軸に、EV 単 TOP5 を相手で 3 連複 1 頭流し |

EV 戦略は「期待値プラスの馬がいないレースは買わない」判断ができる点が ML ベース戦略との違い。

---

## EV（期待値）の定義

```
EV単 = is_place_prob / 3 × 単勝オッズ
EV複 = is_place_prob × 複勝オッズ
```

### 設計上の妥協

- **EV 単**: 本来は単勝確率モデルが必要。`is_place / 3` は近似（複勝確率 ÷ 3 で単勝確率を近似）。
- **オッズ**: KYI の「基準オッズ」「基準複勝オッズ」は発表時点の値。最終オッズと乖離あり。最終オッズ取得は将来課題。
- **複勝オッズ**: 「基準複勝オッズ」は **下限値**（JRDB 仕様）なので、EV はやや保守的に出る。控除側に倒れる。
- **馬連 / 3 連複の真の EV**: 馬連・3 連複の実オッズは未取得。現状の流し戦略は「単勝 EV 上位 N 頭の組合せ」で代用。

---

## 閾値（`--ev-threshold`）

`1.0` がブレイクイーブン（控除前の期待値が 100% = 投資額 = 期待回収額）。

| 閾値 | 意味 |
|------|------|
| `0.9` | 期待値 90%。控除率 20-25% を考えればやや弱気 |
| `1.0` | ブレイクイーブン（デフォルト） |
| `1.2` | 期待値 120%。厳しめにピック |

期間別の感度分析は手動で実施する:

```bash
for thr in 0.9 1.0 1.1 1.2; do
  python cli.py evaluate \
    --date-range 20250101 20251228 \
    --strategy ev_tansho \
    --ev-threshold $thr
done
```

---

## ROI の判定基準（目安）

| ROI | 評価 |
|-----|------|
| ≥ 100% | **実力**。長期回収率プラス |
| 80–100% | **現実的**。控除率 20-25% を考えれば良戦略 |
| 60–80% | 改善余地あり |
| < 60% | ロジック見直しが必要 |

---

## 実行例

```bash
source .venv/bin/activate

# ベースライン（ML 戦略 3 種）
python cli.py evaluate --date-range 20250101 20251228 --strategy fukusho_top3
python cli.py evaluate --date-range 20250101 20251228 --strategy umaren_top2
python cli.py evaluate --date-range 20250101 20251228 --strategy sanrenpuku_top3

# EV 戦略
python cli.py evaluate --date-range 20250101 20251228 --strategy ev_tansho --ev-threshold 1.0
python cli.py evaluate --date-range 20250101 20251228 --strategy ev_fukusho --ev-threshold 1.0
python cli.py evaluate --date-range 20250101 20251228 --strategy ev_sanrenpuku_nagashi --ev-threshold 1.0
```

戦略あたり 5〜15 分（年間 3,400 レースを Modal で逐次予測するため）。

---

## 出力

```
========================================
戦略: ev_tansho, ev>1.0
レース数: 3,453
購入レース数: 1,802
投資額: 540,000円
回収額: 525,300円
回収率: 97.3%
的中数: 287
========================================
```

| 項目 | 説明 |
|------|------|
| `レース数` | 期間内のレース総数 |
| `購入レース数` | EV 戦略で実際にベットしたレース数（軸なしレースはスキップ） |
| `投資額` | 全購入金額の合計 |
| `回収額` | 的中時の払戻金合計 |
| `回収率` | `total_return / total_bets × 100` |
| `的中数` | 当たり券数 |

---

## 実時間予測時の買い目推薦

`predict` コマンドでも EV ランキングと推奨買い目を出力できる:

```bash
python cli.py predict --date 260405 --ev-threshold 1.0
```

非表示にしたい場合は `--no-bet`。

実装: `src/predict/betting.py`
- `compute_expected_values(race_df, predictions)` — レース単位で EV 計算
- `recommend_bets(ev_df, ev_threshold)` — 単複ピック、馬連 BOX、3 連複 BOX を生成

---

## 関連ドキュメント

- CLI コマンド: [docs/CLI.md](CLI.md)
- 特徴量と確率モデル: [docs/FEATURES.md](FEATURES.md)
- アーキテクチャ全体: [docs/ARCHITECTURE.md](ARCHITECTURE.md)
