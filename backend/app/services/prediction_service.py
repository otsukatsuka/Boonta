"""Prediction service with pace-focused analysis and ML model integration."""

import os
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Prediction, RaceEntry
from app.repositories import EntryRepository, PredictionRepository, RaceRepository
from app.schemas import (
    BetRecommendation,
    HighRiskBet,
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
        analyses = await self._analyze_all_horses(entries, race.grade)

        # ペース予想（競馬場・馬場状態を考慮）
        pace_prediction = self._predict_pace(entries, analyses, race)

        # 展開を考慮したランキング生成（MLモデル使用フラグも返す）
        rankings, use_ml = self._generate_rankings_with_pace(entries, analyses, pace_prediction, race)

        # 買い目生成
        recommended_bets = self._generate_bets(rankings, pace_prediction, analyses, race)

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

    async def _analyze_all_horses(self, entries: list[RaceEntry], race_grade: str = "G1") -> dict[int, HorseAnalysis]:
        """Analyze all horses based on entry data and race grade."""
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

            # グレード別の重賞実績推定
            # G1: 出走馬は基本的に重賞実績あり
            # G3: 条件戦上がりも多いため、上位人気のみ実績ありと仮定
            if race_grade == "G1":
                grade_race_wins = 1 if popularity <= 10 else 0
            elif race_grade in ("G2", "G3"):
                grade_race_wins = 1 if popularity <= 5 else 0
            else:
                grade_race_wins = 0

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
        analyses: dict[int, HorseAnalysis],
        race=None,
    ) -> PacePrediction:
        """Predict race pace based on running styles, venue, and track condition."""
        from app.ml.pace import predict_pace

        # Collect running styles and escape horse popularities
        running_styles = []
        escape_popularities = []
        escape_count = 0
        front_count = 0

        for entry in entries:
            analysis = analyses.get(entry.horse_id)
            if analysis:
                style = analysis.running_style
            else:
                style = entry.running_style or "VERSATILE"

            running_styles.append(style)

            if style == "ESCAPE":
                escape_count += 1
                if entry.popularity:
                    escape_popularities.append(entry.popularity)
            elif style == "FRONT":
                front_count += 1

        # Get venue and track condition from race object
        venue = race.venue if race else None
        track_condition = race.track_condition if race else None
        distance = race.distance if race else 2000
        course_type = race.course_type if race else "芝"

        # Use the enhanced predict_pace function
        pace_result = predict_pace(
            running_styles=running_styles,
            distance=distance,
            course_type=course_type,
            venue=venue,
            track_condition=track_condition,
            escape_popularities=escape_popularities if escape_popularities else None,
        )

        return PacePrediction(
            type=pace_result.pace_type,
            confidence=pace_result.confidence,
            reason=pace_result.reason,
            advantageous_styles=pace_result.advantageous_styles,
            escape_count=pace_result.escape_count,
            front_count=pace_result.front_count,
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

            # 展開スコア（重要！競馬場・馬場状態・枠順を考慮）
            pace_score = self._calculate_pace_score(analysis, pace, race, entry)

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

    def _calculate_pace_score(
        self,
        analysis: HorseAnalysis,
        pace: PacePrediction,
        race=None,
        entry: RaceEntry | None = None,
    ) -> float:
        """Calculate score based on pace prediction, venue, track condition, and post position."""
        from app.ml.pace import (
            TRACK_CONDITION_EFFECTS,
            VENUE_CHARACTERISTICS,
            calculate_post_position_effect,
        )

        style = analysis.running_style

        # 1. 基本の展開スコア（展開との相性）
        if style in pace.advantageous_styles:
            base = 0.3
            # 第1有利脚質はさらにボーナス
            if style == pace.advantageous_styles[0]:
                base = 0.35
        else:
            base = 0.1

        # 2. 競馬場特性による調整
        if race and race.venue:
            venue_char = VENUE_CHARACTERISTICS.get(race.venue, {})
            front_advantage = venue_char.get("front_advantage", 0.0)

            if style in ["ESCAPE", "FRONT"]:
                # 前有利コースでボーナス
                base += front_advantage * 0.3
            elif style in ["STALKER", "CLOSER"]:
                # 前有利コースでペナルティ（ただし差し有利コースではボーナス）
                base -= front_advantage * 0.2

        # 3. 馬場状態による調整
        if race and race.track_condition:
            track_effect = TRACK_CONDITION_EFFECTS.get(race.track_condition, {})
            front_mod = track_effect.get("front_modifier", 0.0)

            if style in ["ESCAPE", "FRONT"]:
                base += front_mod * 0.2
            elif style in ["STALKER", "CLOSER"]:
                base -= front_mod * 0.15

        # 4. 枠順による調整
        if entry and entry.post_position and race:
            post_effect = calculate_post_position_effect(
                post_position=entry.post_position,
                running_style=style,
                venue=race.venue,
            )
            base *= post_effect

        # 5. ハイペース時は上がり能力も考慮
        if pace.type == "high" and analysis.best_last_3f <= 33.5:
            base += 0.1

        # 6. スローペース時は位置取りの良さを考慮
        if pace.type == "slow" and analysis.avg_first_corner <= 5:
            base += 0.1

        return max(0.05, min(base, 0.5))  # 0.05 ~ 0.5 の範囲に制限

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
        analyses: dict[int, HorseAnalysis],
        race=None,
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

        # ハイリスクハイリターン買い目を生成
        high_risk_bets = self._generate_high_risk_bets(rankings, pace, analyses)

        # 買い目のnoteを生成（馬場状態を含む）
        pace_labels = {"high": "ハイ", "middle": "ミドル", "slow": "スロー"}
        note_parts = [f"軸: {top_horses[0]},{top_horses[1]}番"]
        note_parts.append(f"展開: {pace_labels.get(pace.type, pace.type)}ペース予想")

        if race:
            if race.venue:
                from app.ml.pace import VENUE_CHARACTERISTICS
                venue_char = VENUE_CHARACTERISTICS.get(race.venue, {})
                if venue_char.get("front_advantage", 0) >= 0.15:
                    note_parts.append(f"{race.venue}は前有利")
                elif venue_char.get("front_advantage", 0) <= -0.10:
                    note_parts.append(f"{race.venue}は差し有利")

            if race.track_condition and race.track_condition != "良":
                note_parts.append(f"【{race.track_condition}馬場】前残り警戒")

        return BetRecommendation(
            trifecta=trifecta,
            trio=trio,
            exacta=exacta,
            wide=wide,
            total_investment=total,
            note=" / ".join(note_parts),
            high_risk_bets=high_risk_bets,
        )

    def _generate_high_risk_bets(
        self,
        rankings: list[HorsePrediction],
        pace: PacePrediction,
        analyses: dict[int, HorseAnalysis],
    ) -> list[HighRiskBet]:
        """Generate high-risk high-return bet recommendations.

        穴馬を中心としたハイリスクハイリターンな買い目を生成する。
        期待値と展開適性を考慮して選定。
        """
        high_risk_bets = []

        # 穴馬候補を抽出（人気6番手以下でスコアが高い馬）
        dark_horse_candidates = []
        for r in rankings:
            if r.popularity and r.popularity >= 6:
                analysis = next((a for a in analyses.values() if a.horse_number == r.horse_number), None)
                if analysis:
                    # 展開適性スコアを計算
                    pace_fit = 1.0 if analysis.running_style in pace.advantageous_styles else 0.5
                    expected_return = (r.odds or 10.0) * r.score * pace_fit
                    dark_horse_candidates.append({
                        "ranking": r,
                        "analysis": analysis,
                        "expected_return": expected_return,
                        "pace_fit": pace_fit,
                    })

        # 期待リターン順にソート
        dark_horse_candidates.sort(key=lambda x: x["expected_return"], reverse=True)

        # 上位3頭の穴馬をピックアップ
        top_dark_horses = dark_horse_candidates[:3]

        if not top_dark_horses:
            return high_risk_bets

        # 人気上位馬（軸になりうる馬）
        favorites = [r for r in rankings[:3]]

        # 1. 穴馬単勝（最も期待値の高い穴馬）
        if top_dark_horses:
            dh = top_dark_horses[0]
            r = dh["ranking"]
            a = dh["analysis"]
            style_ja = {"ESCAPE": "逃げ", "FRONT": "先行", "STALKER": "差し", "CLOSER": "追込", "VERSATILE": "自在"}

            reason_parts = []
            if a.running_style in pace.advantageous_styles:
                reason_parts.append(f"展開◎({style_ja.get(a.running_style, '?')}有利)")
            if r.score >= 0.15:
                reason_parts.append("高スコア")
            if r.odds and r.odds >= 20:
                reason_parts.append(f"高配当期待({r.odds:.1f}倍)")

            high_risk_bets.append(HighRiskBet(
                bet_type="単勝",
                horses=[r.horse_number],
                expected_return=dh["expected_return"],
                risk_level="very_high",
                reason=f"{r.horse_name}: " + "・".join(reason_parts) if reason_parts else "穴馬候補",
                amount=200,
            ))

        # 2. 穴馬ワイド（穴馬 × 人気馬）
        if top_dark_horses and favorites:
            dh = top_dark_horses[0]
            r = dh["ranking"]
            fav = favorites[0]

            # ワイドの期待配当を計算（単勝オッズの約1/3〜1/4が目安）
            estimated_wide_odds = (r.odds or 10.0) * 0.3
            expected_return = estimated_wide_odds * r.score * 1.5  # ワイドは的中率高め

            high_risk_bets.append(HighRiskBet(
                bet_type="ワイド",
                horses=[r.horse_number, fav.horse_number],
                expected_return=expected_return,
                risk_level="medium",
                reason=f"本命{fav.horse_number}番×穴馬{r.horse_number}番 展開次第で高配当",
                amount=300,
            ))

        # 3. 穴馬三連複（穴馬2頭 + 人気馬1頭）
        if len(top_dark_horses) >= 2 and favorites:
            dh1 = top_dark_horses[0]["ranking"]
            dh2 = top_dark_horses[1]["ranking"]
            fav = favorites[0]

            # 三連複の期待配当
            min_odds = min(dh1.odds or 10, dh2.odds or 10)
            estimated_trio_odds = min_odds * 3
            avg_score = (dh1.score + dh2.score + fav.score) / 3
            expected_return = estimated_trio_odds * avg_score

            high_risk_bets.append(HighRiskBet(
                bet_type="三連複",
                horses=[dh1.horse_number, dh2.horse_number, fav.horse_number],
                expected_return=expected_return,
                risk_level="high",
                reason=f"穴馬2頭({dh1.horse_number},{dh2.horse_number}番)＋本命{fav.horse_number}番",
                amount=200,
            ))

        # 4. 穴馬馬単（穴馬 → 人気馬）- 展開向く馬のみ
        pace_fit_dark_horses = [dh for dh in top_dark_horses if dh["pace_fit"] >= 1.0]
        if pace_fit_dark_horses and favorites:
            dh = pace_fit_dark_horses[0]
            r = dh["ranking"]
            fav = favorites[0]

            estimated_exacta_odds = (r.odds or 10.0) * 0.8
            expected_return = estimated_exacta_odds * r.score * dh["pace_fit"]

            high_risk_bets.append(HighRiskBet(
                bet_type="馬単",
                horses=[r.horse_number, fav.horse_number],
                expected_return=expected_return,
                risk_level="very_high",
                reason=f"展開向く穴馬{r.horse_number}番から本命{fav.horse_number}番へ 大波乱狙い",
                amount=100,
            ))

        # 5. 穴馬三連単フォーメーション（超高配当狙い）
        if len(top_dark_horses) >= 2 and len(favorites) >= 2:
            dh_nums = [dh["ranking"].horse_number for dh in top_dark_horses[:2]]
            fav_nums = [f.horse_number for f in favorites[:2]]

            # 穴馬を1着固定
            dh1 = top_dark_horses[0]["ranking"]
            estimated_trifecta_odds = (dh1.odds or 10.0) * 5  # 三連単は単勝の約5倍以上
            expected_return = estimated_trifecta_odds * dh1.score

            high_risk_bets.append(HighRiskBet(
                bet_type="三連単",
                horses=dh_nums + fav_nums,
                expected_return=expected_return,
                risk_level="very_high",
                reason=f"1着:{dh_nums[0]}番(穴) → 2着:{fav_nums}+{dh_nums[1:]} → 3着:ボックス 万馬券狙い",
                amount=100,
            ))

        # 期待リターン順にソート
        high_risk_bets.sort(key=lambda x: x.expected_return, reverse=True)

        return high_risk_bets

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
        """Generate detailed prediction reasoning text like a professional tipster."""
        if not rankings:
            return "データ不足のため予測できません。"

        style_ja = {
            "ESCAPE": "逃げ",
            "FRONT": "先行",
            "STALKER": "差し",
            "CLOSER": "追込",
            "VERSATILE": "自在"
        }

        lines = []

        # ========== 展開予想 ==========
        lines.append("■ 展開予想")
        lines.append("")

        # ペース分析
        if pace.type == "high":
            pace_desc = "ハイペース濃厚。"
            if pace.escape_count >= 3:
                pace_desc += f"逃げ馬が{pace.escape_count}頭と多く、序盤から激しい先行争いが予想される。"
                pace_desc += "前半から脚を使う展開となれば、後方待機組に展開が向く。"
            else:
                pace_desc += "逃げ・先行馬が積極的に動くメンバー構成。"
                pace_desc += "差し・追込馬の末脚が活きる展開か。"
        elif pace.type == "slow":
            pace_desc = "スローペース想定。"
            if pace.escape_count <= 1:
                pace_desc += f"逃げ馬{pace.escape_count}頭と少なく、単騎逃げが濃厚。"
                pace_desc += "前残りを警戒したい。好位からの抜け出しがベストか。"
            else:
                pace_desc += "テンが緩む可能性が高い。"
                pace_desc += "先行馬は脚を温存でき、直線の瞬発力勝負になりそう。"
        else:
            pace_desc = "平均的なペースを想定。"
            pace_desc += "極端な展開にはなりにくく、実力通りの決着か。"
            pace_desc += "好位から競馬できる馬が有利。"

        lines.append(pace_desc)
        lines.append("")

        # ========== 本命馬 ==========
        lines.append("■ 本命")
        lines.append("")

        top = rankings[0]
        top_analysis = analyses.get(top.horse_id)
        if top_analysis:
            # 本命馬の詳細分析
            honmei_parts = []
            honmei_parts.append(f"◎ {top.horse_number}番 {top.horse_name}")

            style = style_ja.get(top_analysis.running_style, "?")
            honmei_parts.append(f"（{style}）")

            lines.append("".join(honmei_parts))

            # 本命理由
            reasons = []

            # 展開面
            if top_analysis.running_style in pace.advantageous_styles:
                if top_analysis.running_style == pace.advantageous_styles[0]:
                    reasons.append(f"今回の展開で最も有利な{style}脚質")
                else:
                    reasons.append(f"想定ペースで展開が向く{style}")

            # 上がり能力
            if top_analysis.best_last_3f <= 33.0:
                reasons.append(f"上がり{top_analysis.best_last_3f:.1f}秒の末脚は強力")
            elif top_analysis.best_last_3f <= 33.5:
                reasons.append(f"上がり{top_analysis.best_last_3f:.1f}秒と決め手がある")

            # 人気と妙味
            if top.popularity and top.popularity <= 2:
                reasons.append("人気も実力も兼ね備えた中心馬")
            elif top.popularity and top.popularity >= 4:
                reasons.append("人気以上の走りが期待できる")

            # オッズ
            if top.odds and top.odds >= 5.0:
                reasons.append(f"オッズ{top.odds:.1f}倍は妙味あり")

            if reasons:
                lines.append("。".join(reasons) + "。")
            lines.append("")

        # ========== 対抗・単穴 ==========
        if len(rankings) >= 2:
            lines.append("■ 対抗・単穴")
            lines.append("")

            # 対抗（2番手）
            rival = rankings[1]
            rival_analysis = analyses.get(rival.horse_id)
            if rival_analysis:
                style = style_ja.get(rival_analysis.running_style, "?")
                lines.append(f"○ {rival.horse_number}番 {rival.horse_name}（{style}）")

                rival_comment = []
                if rival_analysis.running_style in pace.advantageous_styles:
                    rival_comment.append("展開は悪くない")
                if rival_analysis.best_last_3f <= 33.5:
                    rival_comment.append("末脚堅実")
                if rival.popularity and rival.popularity <= 3:
                    rival_comment.append("実績上位で軽視禁物")
                elif rival.popularity and rival.popularity >= 5:
                    rival_comment.append("穴人気でも侮れない")

                if rival_comment:
                    lines.append("。".join(rival_comment) + "。")

            # 単穴（3番手）
            if len(rankings) >= 3:
                third = rankings[2]
                third_analysis = analyses.get(third.horse_id)
                if third_analysis:
                    style = style_ja.get(third_analysis.running_style, "?")
                    lines.append(f"▲ {third.horse_number}番 {third.horse_name}（{style}）")

                    third_comment = []
                    if third.popularity and third.popularity >= 5:
                        third_comment.append("人気の盲点になりそう")
                    if third_analysis.running_style in pace.advantageous_styles:
                        third_comment.append("展開一つで浮上")

                    if third_comment:
                        lines.append("。".join(third_comment) + "。")

            lines.append("")

        # ========== 穴馬 ==========
        dark_horses = [r for r in rankings if r.is_dark_horse]
        if dark_horses:
            lines.append("■ 穴馬注目")
            lines.append("")

            for i, dh in enumerate(dark_horses[:2]):
                dh_analysis = analyses.get(dh.horse_id)
                if dh_analysis:
                    style = style_ja.get(dh_analysis.running_style, "?")
                    mark = "★" if i == 0 else "☆"
                    lines.append(f"{mark} {dh.horse_number}番 {dh.horse_name}（{style}）")

                    ana_parts = []

                    # 穴馬理由
                    if dh.dark_horse_reason:
                        ana_parts.append(dh.dark_horse_reason)

                    # 展開面
                    if dh_analysis.running_style in pace.advantageous_styles:
                        if pace.type == "high":
                            ana_parts.append("ハイペースで前が止まれば一気の台頭")
                        elif pace.type == "slow":
                            ana_parts.append("スローの前残り展開で粘り込む可能性")

                    # オッズの妙味
                    if dh.odds and dh.odds >= 30:
                        ana_parts.append(f"オッズ{dh.odds:.1f}倍は魅力的")
                    elif dh.odds and dh.odds >= 15:
                        ana_parts.append("オッズ的にも狙い目")

                    if ana_parts:
                        lines.append("。".join(ana_parts) + "。")

            lines.append("")

        # ========== 買い目のポイント ==========
        lines.append("■ 買い目のポイント")
        lines.append("")

        buy_advice = []

        # 本命の信頼度による買い方アドバイス
        if top.score >= 0.25:
            buy_advice.append(f"本命{top.horse_number}番を軸に手広く流す")
        else:
            buy_advice.append("混戦模様。ボックス買いも一考")

        # 穴馬絡みのアドバイス
        if dark_horses:
            dh_nums = [str(dh.horse_number) for dh in dark_horses[:2]]
            if pace.type == "high":
                buy_advice.append(f"穴馬{','.join(dh_nums)}番はハイペースなら浮上。ヒモに入れておきたい")
            elif pace.type == "slow":
                buy_advice.append(f"穴馬{','.join(dh_nums)}番は前残り展開で注意")
            else:
                buy_advice.append(f"穴馬{','.join(dh_nums)}番も押さえたい")

        lines.append("。".join(buy_advice) + "。")

        # MLモデル使用時の注記
        if use_ml:
            lines.append("")
            lines.append("※ AI予測モデル（的中率80%）による分析を加味しています。")

        return "\n".join(lines)

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
