# Boonta - 競馬予想AI

展開予想を重視した競馬予想アプリケーション。netkeibaからデータを取得し、機械学習モデルと展開分析を組み合わせて予想を行います。

## 特徴

- **展開予想重視**: 逃げ馬・先行馬の数からペースを予測し、有利な脚質を分析
- **MLモデル統合**: AutoGluonによる複勝予測モデル（ROC AUC: 0.845）
- **馬の過去成績分析**: 勝率・複勝率・直近5走平均着順などを特徴量として活用
- **G1/G3対応**: 重賞レースの学習データを自動収集
- **netkeiba連携**: 出馬表・オッズ・過去成績を自動取得

## 技術スタック

### Backend
- Python 3.10+
- FastAPI
- SQLAlchemy (async)
- AutoGluon (ML)
- BeautifulSoup (スクレイピング)

### Frontend
- React 18
- TypeScript
- Vite
- TailwindCSS
- React Query

## セットアップ

### 必要条件
- Python 3.10以上
- Node.js 18以上

### バックエンド

```bash
cd backend

# 仮想環境作成
python3.10 -m venv .venv
source .venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# 起動
uvicorn app.main:app --reload
```

### フロントエンド

```bash
cd frontend

# 依存関係インストール
npm install

# 起動
npm run dev
```

### Docker（オプション）

```bash
docker-compose up -d
```

## 使い方

### 1. レース登録

フロントエンドの「レース登録」からレース情報を入力、またはAPIを使用：

```bash
curl -X POST http://localhost:8000/api/races/ \
  -H "Content-Type: application/json" \
  -d '{"name": "有馬記念", "date": "2024-12-22", "venue": "中山", "course_type": "芝", "distance": 2500, "grade": "G1"}'
```

### 2. 出馬表取得

netkeibaから出馬表を取得：

```bash
# race_id: DBのレースID, netkeiba_race_id: netkeibaのレースID
curl -X POST http://localhost:8000/api/fetch/entries/1 \
  -H "Content-Type: application/json" \
  -d '{"netkeiba_race_id": "202406050811"}'
```

### 3. オッズ・脚質取得（レース終了後）

```bash
curl -X POST http://localhost:8000/api/fetch/odds/1 \
  -H "Content-Type: application/json" \
  -d '{"netkeiba_race_id": "202406050811"}'
```

### 4. 予想実行

```bash
curl -X POST http://localhost:8000/api/predictions/1
```

## MLモデル学習

### データ収集

```bash
cd backend
source .venv/bin/activate

# G1レースのみ収集
python scripts/collect_training_data.py --grade G1

# G3レースのみ収集
python scripts/collect_training_data.py --grade G3

# G1 + G3 両方収集
python scripts/collect_training_data.py --grade all

# 馬の過去成績付きで収集（精度向上、時間がかかる）
python scripts/collect_training_data.py --grade G1 --with-history
```

### G3レースID取得

```bash
# netkeibaからG3レースIDを自動取得
python scripts/fetch_grade_race_ids.py
```

### モデル学習

```bash
# 通常学習
python scripts/train_model.py

# 過去成績特徴量付きで学習（推奨）
python scripts/train_model.py --with-history

# グレード指定
python scripts/train_model.py --grade G1 --with-history
```

### 学習データの特徴量

| カテゴリ | 特徴量 |
|---------|--------|
| 基本情報 | 馬番, オッズ, 人気, 斤量, 馬体重 |
| レース情報 | 距離, コース(芝/ダート), グレード |
| 脚質 | 逃げ/先行/差し/追込 |
| 過去成績 | 勝率, 複勝率, 直近5走平均着順, 重賞勝利数 |
| 上がり | 過去最高上がり3F, 平均上がり3F |

学習データは `backend/data/training/`、モデルは `backend/models/place_predictor/` に保存されます。

## API仕様

起動後、以下でAPIドキュメントを確認できます：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 予測ロジック

### 展開予想

| 逃げ馬数 | ペース | 有利な脚質 |
|---------|--------|-----------|
| 3頭以上 | ハイ | 差し・追込 |
| 2頭 | ハイ | 差し・追込 |
| 1頭（先行少） | スロー | 逃げ・先行 |
| 0頭 | スロー | 先行・差し |

### スコア計算（ML使用時）

| 要素 | 重み |
|-----|------|
| ML予測（複勝確率） | 40% |
| 展開適性 | 25% |
| 上がり能力 | 20% |
| 実績 | 15% |

## ライセンス

MIT

## 注意事項

- netkeibaへのスクレイピングは利用規約を遵守し、適切な間隔を空けて行ってください
- 本ソフトウェアは予想の参考情報を提供するものであり、馬券購入の結果について一切の責任を負いません
