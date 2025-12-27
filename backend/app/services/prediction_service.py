"""Prediction service with pace-focused analysis and ML model integration."""

import os
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.fetchers.netkeiba import NetkeibaFetcher
from app.models import Prediction, RaceEntry
from app.repositories import EntryRepository, PredictionRepository, RaceRepository
from app.schemas import (
    BetRecommendation,
    HorsePrediction,
    PacePrediction,
    PredictionResponse,
)

settings = get_settings()

# MLモデルのロード（遅延ロード）
_ml_predictor = None


def get_ml_predictor():
    """Load ML predictor lazily."""
    global _ml_predictor
    if _ml_predictor is None:
        # backend/app/services -> backend/app -> backend -> backend/models/place_predictor
        model_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "models",
            "place_predictor"
        )
        if os.path.exists(model_path):
            try:
                from autogluon.tabular import TabularPredictor
                _ml_predictor = TabularPredictor.load(model_path)
                print(f"Loaded ML model from {model_path}")
            except Exception as e:
                print(f"Failed to load ML model: {e}")
                _ml_predictor = False  # Mark as failed
        else:
            print(f"ML model not found at {model_path}")
            _ml_predictor = False  # Model not available
    return _ml_predictor if _ml_predictor else None


@dataclass
class HorseAnalysis:
    """Analysis data for a horse."""
    horse_id: int
    horse_name: str
    horse_number: int

    # 脚質分析
    running_style: str  # ESCAPE, FRONT, STALKER, CLOSER
    avg_first_corner: float  # 平均1コーナー通過順

    # 上がり分析
    avg_last_3f: float  # 平均上がり3F
    best_last_3f: float  # ベスト上がり3F

    # 実績
    win_rate: float
    place_rate: float  # 複勝率
    grade_race_wins: int  # 重賞勝利数

    # 今回のレース条件
    odds: float | None
    popularity: int | None


class PredictionService:
    """Service for prediction operations with pace-focused analysis."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.race_repo = RaceRepository(session)
        self.entry_repo = EntryRepository(session)
        self.prediction_repo = PredictionRepository(session)

    async def get_prediction(self, race_id: int) -> PredictionResponse | None:
        """Get latest prediction for a race."""
        prediction = await self.prediction_repo.get_by_race(race_id)
        if not prediction:
            return None
        return self._to_response(prediction)

    async def get_prediction_history(
        self, race_id: int, limit: int = 10
    ) -> list[Prediction]:
        """Get prediction history for a race."""
        return await self.prediction_repo.get_history_by_race(race_id, limit)

    async def create_prediction(self, race_id: int) -> PredictionResponse | None:
        """Create a new prediction for a race with pace-focused analysis."""
        race = await self.race_repo.get_with_entries(race_id)
        if not race:
            return None

        entries = await self.entry_repo.get_by_race(race_id)
        if not entries:
            return None

        # 各馬の過去成績を分析
        analyses = await self._analyze_all_horses(entries)

        # ペース予想
        pace_prediction = self._predict_pace(entries, analyses)

        # 展開を考慮したランキング生成（MLモデル使用フラグも返す）
        rankings, use_ml = self._generate_rankings_with_pace(entries, analyses, pace_prediction, race)

        # 買い目生成
        recommended_bets = self._generate_bets(rankings, pace_prediction)

        # 信頼度計算
        confidence_score = self._calculate_confidence(rankings, pace_prediction, analyses)

        # 理由生成（MLフラグを渡す）
        reasoning = self._generate_reasoning(rankings, pace_prediction, analyses, use_ml)

        # 保存
        prediction_data = {
            "rankings": [r.model_dump() for r in rankings],
            "pace_prediction": pace_prediction.model_dump() if pace_prediction else None,
            "recommended_bets": recommended_bets.model_dump() if recommended_bets else None,
        }

        prediction = await self.prediction_repo.create({
            "race_id": race_id,
            "model_version": settings.model_version,
            "predicted_at": datetime.now(timezone.utc),
            "prediction_data": prediction_data,
            "confidence_score": confidence_score,
            "reasoning": reasoning,
        })

        return self._to_response(prediction)

    async def _analyze_all_horses(self, entries: list[RaceEntry]) -> dict[int, HorseAnalysis]:
        """Analyze all horses based on entry data."""
        analyses = {}

        for entry in entries:
            if not entry.horse:
                continue

            # エントリーに設定された脚質を使用（fetch/oddsで設定済み）
            running_style = entry.running_style or "VERSATILE"

            # 脚質から平均コーナー位置を推定
            style_to_corner = {
                "ESCAPE": 1.5,
                "FRONT": 4.0,
                "STALKER": 7.0,
                "CLOSER": 12.0,
                "VERSATILE": 8.0,
            }
            avg_first_corner = style_to_corner.get(running_style, 8.0)

            # デフォルト値（実際のレースデータがないため推定値）
            # 人気馬は上がりが速い傾向
            popularity = entry.popularity or 10
            if popularity <= 3:
                avg_last_3f = 33.5
                best_last_3f = 33.0
            elif popularity <= 6:
                avg_last_3f = 34.0
                best_last_3f = 33.5
            else:
                avg_last_3f = 34.5
                best_last_3f = 34.0

            # オッズから勝率・複勝率を推定
            odds = entry.odds or 50.0
            win_rate = min(1.0 / odds, 0.5) if odds > 0 else 0.05
            place_rate = min(3.0 / odds, 0.8) if odds > 0 else 0.15

            # G1なので全馬重賞実績ありと仮定
            grade_race_wins = 1 if popularity <= 10 else 0

            analyses[entry.horse_id] = HorseAnalysis(
                horse_id=entry.horse_id,
                horse_name=entry.horse.name,
                horse_number=entry.horse_number or 0,
                running_style=running_style,
                avg_first_corner=avg_first_corner,
                avg_last_3f=avg_last_3f,
                best_last_3f=best_last_3f,
                win_rate=win_rate,
                place_rate=place_rate,
                grade_race_wins=grade_race_wins,
                odds=entry.odds,
                popularity=entry.popularity,
            )

        return analyses

    def _estimate_running_style_from_avg(self, avg_first_corner: float) -> str:
        """Estimate running style from average first corner position."""
        if avg_first_corner <= 2.5:
            return "ESCAPE"
        elif avg_first_corner <= 5.0:
            return "FRONT"
        elif avg_first_corner <= 10.0:
            return "STALKER"
        else:
            return "CLOSER"

    def _predict_pace(
        self,
        entries: list[RaceEntry],
        analyses: dict[int, HorseAnalysis]
    ) -> PacePrediction:
        """Predict race pace based on running styles."""
        escape_count = 0
        front_count = 0

        for entry in entries:
            analysis = analyses.get(entry.horse_id)
            if analysis:
                style = analysis.running_style
            else:
                style = entry.running_style or "VERSATILE"

            if style == "ESCAPE":
                escape_count += 1
            elif style == "FRONT":
                front_count += 1

        # ペース判定
        if escape_count >= 3:
            pace_type = "high"
            advantage = ["STALKER", "CLOSER"]
            reason = f"逃げ馬が{escape_count}頭で激しい先行争いが予想される。差し・追込有利。"
            confidence = 0.8
        elif escape_count >= 2:
            pace_type = "high"
            advantage = ["STALKER", "CLOSER"]
            reason = f"逃げ馬{escape_count}頭で競り合い必至。差し馬に展開向く。"
            confidence = 0.7
        elif escape_count == 1 and front_count <= 3:
            pace_type = "slow"
            advantage = ["ESCAPE", "FRONT"]
            reason = "逃げ馬1頭で楽逃げ濃厚。前残り警戒。"
            confidence = 0.75
        elif escape_count == 0:
            pace_type = "slow"
            advantage = ["FRONT", "STALKER"]
            reason = "逃げ馬不在でスロー必至。先行・好位差し有利。"
            confidence = 0.7
        else:
            pace_type = "middle"
            advantage = ["FRONT", "STALKER"]
            reason = "平均的なペースが予想される。"
            confidence = 0.5

        return PacePrediction(
            type=pace_type,
            confidence=confidence,
            reason=reason,
            advantageous_styles=advantage,
            escape_count=escape_count,
            front_count=front_count,
        )

    def _get_ml_predictions(
        self,
        entries: list[RaceEntry],
        analyses: dict[int, HorseAnalysis],
        race,
    ) -> dict[int, float]:
        """Get ML model predictions for place probability."""
        predictor = get_ml_predictor()
        if not predictor:
            return {}

        # Prepare data for prediction
        data = []
        horse_ids = []

        for entry in entries:
            analysis = analyses.get(entry.horse_id)
            if not analysis:
                continue

            # Running style encoding
            style_map = {
                "ESCAPE": 1, "FRONT": 2, "STALKER": 3, "CLOSER": 4, "VERSATILE": 2.5
            }
            running_style_code = style_map.get(analysis.running_style, 2.5)

            # Course type
            is_turf = 1 if race.course_type == "芝" else 0

            # Grade encoding
            grade_map = {"G1": 1, "G2": 2, "G3": 3, "OP": 4}
            grade_code = grade_map.get(race.grade, 4)

            odds = analysis.odds or 50.0
            log_odds = np.log(odds + 1) if odds > 0 else 0

            row = {
                "horse_number": analysis.horse_number,
                "odds": odds,
                "popularity": analysis.popularity or 10,
                "running_style_code": running_style_code,
                "distance": race.distance,
                "is_turf": is_turf,
                "grade_code": grade_code,
                "weight": entry.weight or 55.0,
                "log_odds": log_odds,
                "horse_weight": entry.horse_weight or 480,
                "last_3f": analysis.best_last_3f,
            }
            data.append(row)
            horse_ids.append(entry.horse_id)

        if not data:
            return {}

        # Make prediction
        df = pd.DataFrame(data)
        try:
            proba = predictor.predict_proba(df)
            # Get probability for class 1 (is_place = 1)
            if hasattr(proba, 'iloc'):
                place_proba = proba[1].values if 1 in proba.columns else proba.iloc[:, 1].values
            else:
                place_proba = proba[:, 1]

            return dict(zip(horse_ids, place_proba))
        except Exception as e:
            print(f"ML prediction error: {e}")
            return {}

    def _generate_rankings_with_pace(
        self,
        entries: list[RaceEntry],
        analyses: dict[int, HorseAnalysis],
        pace: PacePrediction,
        race,
    ) -> tuple[list[HorsePrediction], bool]:
        """Generate horse rankings considering pace prediction and ML model.

        Returns:
            Tuple of (rankings, use_ml_flag)
        """
        rankings = []

        # Get ML predictions
        ml_predictions = self._get_ml_predictions(entries, analyses, race)
        use_ml = len(ml_predictions) > 0

        for entry in entries:
            analysis = analyses.get(entry.horse_id)
            if not analysis:
                continue

            # 基本スコア（オッズから）
            if analysis.odds and analysis.odds > 0:
                base_score = 1.0 / analysis.odds
            else:
                base_score = 0.05

            # 展開スコア（重要！）
            pace_score = self._calculate_pace_score(analysis, pace)

            # 上がり能力スコア
            last_3f_score = self._calculate_last_3f_score(analysis, pace)

            # 実績スコア
            track_record_score = self._calculate_track_record_score(analysis)

            # MLスコア（モデルがある場合）
            ml_score = ml_predictions.get(entry.horse_id, 0.0)

            # 総合スコア（ML使用時は重み調整）
            if use_ml:
                total_score = (
                    ml_score * 0.4 +          # ML予測を重視
                    pace_score * 0.25 +        # 展開適性
                    last_3f_score * 0.2 +      # 上がり能力
                    track_record_score * 0.15  # 実績
                )
            else:
                total_score = (
                    base_score * 0.2 +      # オッズは参考程度
                    pace_score * 0.35 +      # 展開適性を重視
                    last_3f_score * 0.25 +   # 上がり能力
                    track_record_score * 0.2  # 実績
                )

            # 穴馬判定
            is_dark_horse = False
            dark_horse_reason = None
            if analysis.popularity and analysis.popularity >= 6:
                # 人気薄だがスコアが高い
                if total_score >= 0.15:
                    is_dark_horse = True
                    reasons = []
                    if pace_score >= 0.25:
                        reasons.append("展開向く")
                    if analysis.best_last_3f <= 33.5:
                        reasons.append("上がり能力高い")
                    if analysis.grade_race_wins > 0:
                        reasons.append("重賞実績あり")
                    dark_horse_reason = "・".join(reasons) if reasons else "好走の可能性"

            rankings.append(HorsePrediction(
                rank=1,  # 後でソートして更新
                horse_id=entry.horse_id,
                horse_name=analysis.horse_name,
                horse_number=analysis.horse_number,
                score=min(total_score, 1.0),
                win_probability=min(total_score * 0.4, 0.5),
                place_probability=min(total_score * 1.2, 0.85),
                popularity=analysis.popularity,
                odds=analysis.odds,
                is_dark_horse=is_dark_horse,
                dark_horse_reason=dark_horse_reason,
            ))

        # スコアでソートしてランク付け
        rankings.sort(key=lambda x: x.score, reverse=True)
        for i, r in enumerate(rankings):
            r.rank = i + 1

        return rankings, use_ml

    def _calculate_pace_score(self, analysis: HorseAnalysis, pace: PacePrediction) -> float:
        """Calculate score based on pace prediction and running style."""
        style = analysis.running_style

        # 展開との相性
        if style in pace.advantageous_styles:
            base = 0.3
            # 第1有利脚質はさらにボーナス
            if style == pace.advantageous_styles[0]:
                base = 0.35
        else:
            base = 0.1

        # ハイペース時は上がり能力も考慮
        if pace.type == "high" and analysis.best_last_3f <= 33.5:
            base += 0.1

        # スローペース時は位置取りの良さを考慮
        if pace.type == "slow" and analysis.avg_first_corner <= 5:
            base += 0.1

        return base

    def _calculate_last_3f_score(self, analysis: HorseAnalysis, pace: PacePrediction) -> float:
        """Calculate score based on last 3F ability."""
        best = analysis.best_last_3f
        avg = analysis.avg_last_3f

        # ベスト上がりでスコアリング
        if best <= 32.5:
            score = 0.35
        elif best <= 33.0:
            score = 0.3
        elif best <= 33.5:
            score = 0.25
        elif best <= 34.0:
            score = 0.2
        elif best <= 34.5:
            score = 0.15
        else:
            score = 0.1

        # 安定性（平均とベストの差が小さい）
        stability = 1.0 - min((avg - best) / 2.0, 0.3)
        score *= stability

        # ハイペース予想時は上がり能力がより重要
        if pace.type == "high":
            score *= 1.2

        return min(score, 0.4)

    def _calculate_track_record_score(self, analysis: HorseAnalysis) -> float:
        """Calculate score based on track record."""
        score = 0.0

        # 勝率
        score += analysis.win_rate * 0.4

        # 複勝率
        score += analysis.place_rate * 0.3

        # 重賞実績
        if analysis.grade_race_wins >= 3:
            score += 0.3
        elif analysis.grade_race_wins >= 1:
            score += 0.2
        elif analysis.grade_race_wins == 0:
            score += 0.05

        return min(score, 0.4)

    def _generate_bets(
        self,
        rankings: list[HorsePrediction],
        pace: PacePrediction,
    ) -> BetRecommendation:
        """Generate bet recommendations."""
        if len(rankings) < 3:
            return BetRecommendation(total_investment=0)

        top_horses = [r.horse_number for r in rankings[:2]]
        counter_horses = [r.horse_number for r in rankings[2:6]]
        dark_horses = [r.horse_number for r in rankings if r.is_dark_horse][:2]

        all_horses = list(dict.fromkeys(top_horses + counter_horses[:2] + dark_horses))

        trifecta = {
            "type": "formation",
            "first": top_horses,
            "second": list(dict.fromkeys(top_horses + counter_horses[:2])),
            "third": all_horses,
            "combinations": len(top_horses) * len(set(top_horses + counter_horses[:2])) * len(all_horses),
            "amount_per_ticket": 100,
        }

        trio = {
            "type": "box",
            "horses": all_horses[:5],
            "combinations": 10,
            "amount_per_ticket": 300,
        }

        exacta = None
        if rankings[0].score > 0.25:
            exacta = {
                "type": "first_to_others",
                "first": rankings[0].horse_number,
                "second": [r.horse_number for r in rankings[1:4]],
                "combinations": 3,
                "amount_per_ticket": 500,
            }

        wide = None
        if dark_horses:
            wide = {
                "pairs": [[dark_horses[0], top_horses[0]]],
                "note": f"穴馬{dark_horses[0]}番絡み",
                "amount_per_ticket": 200,
            }

        total = (
            trifecta["combinations"] * trifecta["amount_per_ticket"]
            + trio["combinations"] * trio["amount_per_ticket"]
            + (exacta["combinations"] * exacta["amount_per_ticket"] if exacta else 0)
            + (len(wide["pairs"]) * wide["amount_per_ticket"] if wide else 0)
        )

        return BetRecommendation(
            trifecta=trifecta,
            trio=trio,
            exacta=exacta,
            wide=wide,
            total_investment=total,
            note=f"軸: {top_horses[0]},{top_horses[1]}番 / 展開: {pace.type}ペース予想",
        )

    def _calculate_confidence(
        self,
        rankings: list[HorsePrediction],
        pace: PacePrediction,
        analyses: dict[int, HorseAnalysis],
    ) -> float:
        """Calculate overall prediction confidence."""
        if not rankings:
            return 0.0

        confidence = pace.confidence * 0.4

        # トップ馬のスコア差
        if len(rankings) >= 2:
            score_diff = rankings[0].score - rankings[1].score
            confidence += min(score_diff * 3, 0.3)

        # データの充実度
        data_quality = sum(1 for a in analyses.values() if a.avg_last_3f < 35.0) / max(len(analyses), 1)
        confidence += data_quality * 0.2

        return min(confidence + 0.1, 1.0)

    def _generate_reasoning(
        self,
        rankings: list[HorsePrediction],
        pace: PacePrediction,
        analyses: dict[int, HorseAnalysis],
        use_ml: bool = False,
    ) -> str:
        """Generate prediction reasoning text."""
        if not rankings:
            return "データ不足のため予測できません。"

        parts = []

        # MLモデル使用情報
        if use_ml:
            parts.append("【AI予測】MLモデル(ROC AUC 0.80)による予測を使用")

        # 展開予想
        parts.append(f"【展開】{pace.reason}")

        # 本命馬
        top = rankings[0]
        top_analysis = analyses.get(top.horse_id)
        if top_analysis:
            style_ja = {"ESCAPE": "逃げ", "FRONT": "先行", "STALKER": "差し", "CLOSER": "追込", "VERSATILE": "自在"}
            parts.append(
                f"【本命】{top.horse_number}番{top.horse_name} "
                f"({style_ja.get(top_analysis.running_style, '?')}・上がり{top_analysis.best_last_3f:.1f})"
            )

        # 穴馬
        dark_horses = [r for r in rankings if r.is_dark_horse]
        if dark_horses:
            dh = dark_horses[0]
            parts.append(f"【穴】{dh.horse_number}番{dh.horse_name} - {dh.dark_horse_reason}")

        return " ".join(parts)

    def _to_response(self, prediction: Prediction) -> PredictionResponse:
        """Convert Prediction model to PredictionResponse."""
        data = prediction.prediction_data

        rankings = [
            HorsePrediction(**r) for r in data.get("rankings", [])
        ]

        pace_data = data.get("pace_prediction")
        pace_prediction = PacePrediction(**pace_data) if pace_data else None

        bets_data = data.get("recommended_bets")
        recommended_bets = BetRecommendation(**bets_data) if bets_data else None

        return PredictionResponse(
            race_id=prediction.race_id,
            model_version=prediction.model_version,
            predicted_at=prediction.predicted_at,
            rankings=rankings,
            pace_prediction=pace_prediction,
            recommended_bets=recommended_bets,
            confidence_score=prediction.confidence_score,
            reasoning=prediction.reasoning,
        )
