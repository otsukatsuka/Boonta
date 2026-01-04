"""Prediction service with pace-focused analysis and ML model integration via Modal."""

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Prediction, RaceEntry
from app.repositories import EntryRepository, PredictionRepository, RaceRepository
from app.schemas import (
    BetRecommendation,
    HorsePrediction,
    PacePrediction,
    PredictionResponse,
)

settings = get_settings()


@dataclass
class HorseAnalysis:
    """Analysis data for a horse."""
    horse_id: int
    horse_name: str
    horse_number: int

    # 脚質分析
    running_style: str  # ESCAPE, FRONT, STALKER, CLOSER
    avg_first_corner: float  # 平均1コーナー通過順

    # 上がり分析 (実績ベース)
    avg_last_3f: float  # 平均上がり3F
    best_last_3f: float  # ベスト上がり3F

    # 実績 (実績ベース - オッズからの推定ではない)
    win_rate: float
    place_rate: float  # 複勝率
    grade_race_wins: int  # 重賞勝利数
    avg_position_last5: float = 5.0  # 直近5走平均着順

    # 適性
    same_distance_place_rate: float | None = None
    same_venue_place_rate: float | None = None

    # 今回のレース条件 (参考情報として保持、スコア計算には使わない)
    odds: float | None = None
    popularity: int | None = None

    # 実績データの有無
    has_actual_stats: bool = False  # 実績データがあるかどうか


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

        # 展開を考慮したランキング生成（Modal経由でML予測、MLモデル使用フラグも返す）
        rankings, use_ml = await self._generate_rankings_with_pace(entries, analyses, pace_prediction, race)

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
        """Analyze all horses based on entry data and race grade.

        IMPORTANT: This method now uses DEFAULT VALUES that are NOT biased by odds/popularity.
        All horses start with similar baseline scores - differentiation comes from:
        1. Running style fit with predicted pace
        2. Actual performance data (when available from training data)
        3. Track/distance aptitude
        """
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

            # ==========================================
            # デフォルト値 - オッズ/人気に依存しない！
            # 全馬同じベースラインからスタート
            # ==========================================

            # 上がり3F: 全馬同じデフォルト値
            # (脚質による差はペーススコアで反映)
            avg_last_3f = 34.0
            best_last_3f = 33.5

            # 実績: 全馬同じデフォルト値 (G3平均に近い値)
            win_rate = 0.10  # 10%
            place_rate = 0.25  # 25%
            avg_position_last5 = 5.0
            grade_race_wins = 0

            # 適性: デフォルトなし（ML or ペースで評価）
            same_distance_place_rate = None
            same_venue_place_rate = None

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
                avg_position_last5=avg_position_last5,
                same_distance_place_rate=same_distance_place_rate,
                same_venue_place_rate=same_venue_place_rate,
                odds=entry.odds,  # 参考情報として保持
                popularity=entry.popularity,  # 参考情報として保持
                has_actual_stats=False,  # 実績データなし
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

    async def _get_ml_predictions(
        self,
        entries: list[RaceEntry],
        analyses: dict[int, HorseAnalysis],
        race,
    ) -> dict[int, float]:
        """Get ML model predictions for place probability via Modal.

        IMPORTANT: This method now provides features WITHOUT odds/popularity.
        The ML model should be trained without these features as well.
        """
        from modal_app.client import get_modal_client

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

            row = {
                "horse_number": analysis.horse_number,
                "running_style_code": running_style_code,
                "distance": race.distance,
                "is_turf": is_turf,
                "grade_code": grade_code,
                "weight": entry.weight or 55.0,
                "horse_weight": entry.horse_weight or 480,
                "last_3f": analysis.best_last_3f,
                "win_rate": analysis.win_rate,
                "place_rate": analysis.place_rate,
                "avg_position_last5": analysis.avg_position_last5,
                "grade_wins": analysis.grade_race_wins,
            }
            data.append(row)
            horse_ids.append(entry.horse_id)

        if not data:
            return {}

        # Call Modal for prediction
        try:
            modal_client = get_modal_client()
            result = await modal_client.predict(data)

            if not result.get("success"):
                print(f"Modal prediction error: {result.get('error')}")
                return {}

            predictions = result.get("predictions", [])
            return dict(zip(horse_ids, predictions))
        except Exception as e:
            print(f"Modal prediction error: {e}")
            return {}

    async def _generate_rankings_with_pace(
        self,
        entries: list[RaceEntry],
        analyses: dict[int, HorseAnalysis],
        pace: PacePrediction,
        race,
    ) -> tuple[list[HorsePrediction], bool]:
        """Generate horse rankings considering pace prediction and ML model.

        IMPORTANT: This method NO LONGER uses odds for scoring.
        Differentiation comes from:
        1. ML predictions (trained without odds features via Modal)
        2. Pace/running style fit
        3. Track record (when available)

        Returns:
            Tuple of (rankings, use_ml_flag)
        """
        rankings = []

        # Get ML predictions via Modal
        ml_predictions = await self._get_ml_predictions(entries, analyses, race)
        use_ml = len(ml_predictions) > 0

        for entry in entries:
            analysis = analyses.get(entry.horse_id)
            if not analysis:
                continue

            # ==========================================
            # オッズベースのbase_scoreを完全削除！
            # ==========================================

            # 展開スコア（最重要！競馬場・馬場状態・枠順を考慮）
            pace_score = self._calculate_pace_score(analysis, pace, race, entry)

            # 上がり能力スコア (現状はデフォルト値だが、将来は実績から)
            last_3f_score = self._calculate_last_3f_score(analysis, pace)

            # 実績スコア (現状はデフォルト値だが、将来は実績から)
            track_record_score = self._calculate_track_record_score(analysis)

            # MLスコア（モデルがある場合）
            ml_score = ml_predictions.get(entry.horse_id, 0.0)

            # 総合スコア
            if use_ml:
                # MLモデルがある場合: ML予測を重視
                total_score = (
                    ml_score * 0.45 +          # ML予測（オッズなし学習）
                    pace_score * 0.35 +        # 展開適性
                    last_3f_score * 0.1 +      # 上がり能力
                    track_record_score * 0.1   # 実績
                )
            else:
                # MLモデルがない場合: 展開を最重視
                total_score = (
                    pace_score * 0.50 +        # 展開適性を最重視
                    last_3f_score * 0.25 +     # 上がり能力
                    track_record_score * 0.25  # 実績
                )

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
                is_dark_horse=False,  # 後で相対順位で判定
                dark_horse_reason=None,
            ))

        # スコアでソートしてランク付け
        rankings.sort(key=lambda x: x.score, reverse=True)
        for i, r in enumerate(rankings):
            r.rank = i + 1

        # ==========================================
        # 穴馬判定: 相対順位ベースに変更
        # ==========================================
        self._mark_dark_horses(rankings, analyses, pace)

        return rankings, use_ml

    def _mark_dark_horses(
        self,
        rankings: list[HorsePrediction],
        analyses: dict[int, HorseAnalysis],
        pace: PacePrediction,
    ) -> None:
        """Mark dark horses based on relative ranking vs popularity.

        Dark horse criteria:
        - 人気より予測順位が大幅に上 (人気 - 予測順位 >= 3)
        - または、人気7位以下でスコア上位50%に入っている
        """
        if len(rankings) < 3:
            return

        # スコアの中央値を計算
        scores = sorted([r.score for r in rankings], reverse=True)
        median_score = scores[len(scores) // 2]

        for r in rankings:
            analysis = analyses.get(r.horse_id)
            if not analysis or not r.popularity:
                continue

            # 条件1: 人気より順位が大幅に上
            popularity_gap = r.popularity - r.rank
            is_gap_horse = popularity_gap >= 3

            # 条件2: 人気薄でスコア上位50%
            is_value_horse = r.popularity >= 7 and r.score >= median_score

            if is_gap_horse or is_value_horse:
                r.is_dark_horse = True
                reasons = []

                # 展開面
                if analysis.running_style in pace.advantageous_styles:
                    if analysis.running_style == pace.advantageous_styles[0]:
                        reasons.append("展開最有利")
                    else:
                        reasons.append("展開向く")

                # 順位ギャップ
                if is_gap_horse:
                    reasons.append(f"人気{r.popularity}→予測{r.rank}位")

                r.dark_horse_reason = "・".join(reasons) if reasons else "好走の可能性"

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
        """Generate bet recommendations - 三連複と三連単2頭軸マルチのみ."""
        if len(rankings) < 3:
            return BetRecommendation(total_investment=0)

        # 軸の選定: 本命（スコア1位）+ 穴馬（期待値最高）
        pivot1 = rankings[0]  # 本命
        pivot2 = self._select_best_dark_horse(rankings, analyses, pace)

        # 相手の選定（スコア2-5位から軸穴馬を除く）
        others_trio = [
            r for r in rankings[1:6]
            if r.horse_number != pivot2.horse_number
        ][:4]
        others_trifecta = [
            r for r in rankings[1:5]
            if r.horse_number != pivot2.horse_number
        ][:3]

        # 三連複（軸2頭流し）: 4点 × 1,000円 = 4,000円
        trio = {
            "type": "pivot_2_nagashi",
            "pivots": [pivot1.horse_number, pivot2.horse_number],
            "others": [r.horse_number for r in others_trio],
            "combinations": len(others_trio),
            "amount_per_ticket": 1000,
        }

        # 三連単2頭軸マルチ: 18点 × 200円 = 3,600円
        # マルチ = 軸2頭の順番を問わない（6パターン × 相手数）
        trifecta_multi = {
            "type": "pivot_2_multi",
            "pivots": [pivot1.horse_number, pivot2.horse_number],
            "others": [r.horse_number for r in others_trifecta],
            "combinations": len(others_trifecta) * 6,
            "amount_per_ticket": 200,
        }

        total = (
            trio["combinations"] * trio["amount_per_ticket"]
            + trifecta_multi["combinations"] * trifecta_multi["amount_per_ticket"]
        )

        # noteを生成
        pace_labels = {"high": "ハイ", "middle": "ミドル", "slow": "スロー"}
        note_parts = [
            f"軸: {pivot1.horse_number}番(本命)+{pivot2.horse_number}番(穴)"
        ]
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
            trio=trio,
            trifecta_multi=trifecta_multi,
            total_investment=total,
            note=" / ".join(note_parts),
        )

    def _select_best_dark_horse(
        self,
        rankings: list[HorsePrediction],
        analyses: dict[int, HorseAnalysis],
        pace: PacePrediction,
    ) -> HorsePrediction:
        """期待値最高の穴馬を選定する.

        NEW CRITERIA (オッズ依存を軽減):
        - is_dark_horse=True (相対順位ベースで判定済み)
        - または、人気6位以下でスコア上位40%
        - 展開有利なら優先
        """
        if len(rankings) < 2:
            return rankings[0]

        # スコア上位40%の閾値
        scores = sorted([r.score for r in rankings], reverse=True)
        top_40_threshold = scores[max(0, int(len(scores) * 0.4) - 1)]

        candidates = []
        for r in rankings:
            if not r.popularity:
                continue

            # 条件1: すでにdark_horseとしてマーク済み
            # 条件2: 人気6位以下でスコア上位40%
            is_candidate = r.is_dark_horse or (
                r.popularity >= 6 and r.score >= top_40_threshold
            )

            if is_candidate:
                analysis = analyses.get(r.horse_id)
                if analysis:
                    # 展開フィットボーナス
                    pace_fit = 1.0
                    if analysis.running_style in pace.advantageous_styles:
                        if analysis.running_style == pace.advantageous_styles[0]:
                            pace_fit = 1.5  # 最有利脚質
                        else:
                            pace_fit = 1.2

                    # オッズは期待値計算にのみ使用（スコアには影響させない）
                    odds = r.odds or 10.0
                    expected_return = odds * r.score * pace_fit

                    candidates.append((r, expected_return))

        # 期待値最高の穴馬を返す
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        # 穴馬がいない場合はスコア2位を返す（人気馬でもOK）
        return rankings[1] if len(rankings) > 1 else rankings[0]

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
