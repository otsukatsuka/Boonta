"""Feature engineering service."""

from datetime import date

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import EntryRepository, HorseRepository, ResultRepository


class FeatureService:
    """Service for feature engineering."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.horse_repo = HorseRepository(session)
        self.entry_repo = EntryRepository(session)
        self.result_repo = ResultRepository(session)

    async def build_features_for_entry(
        self, entry_id: int, race_date: date
    ) -> dict | None:
        """Build features for a single race entry."""
        entry = await self.entry_repo.get_with_relations(entry_id)
        if not entry:
            return None

        horse_results = await self.result_repo.get_by_horse(entry.horse_id, limit=10)

        features = {
            # Horse basic info
            "horse_age": entry.horse.age if entry.horse else None,
            "horse_sex": entry.horse.sex if entry.horse else None,
            "horse_weight": entry.horse_weight,
            "horse_weight_diff": entry.horse_weight_diff,
            # Race conditions
            "distance": entry.race.distance if entry.race else None,
            "course_type": entry.race.course_type if entry.race else None,
            "venue": entry.race.venue if entry.race else None,
            "track_condition": entry.race.track_condition if entry.race else None,
            "weather": entry.race.weather if entry.race else None,
            "post_position": entry.post_position,
            "horse_number": entry.horse_number,
            "weight": entry.weight,
            # Odds
            "odds": entry.odds,
            "popularity": entry.popularity,
            # Running style
            "running_style": entry.running_style,
            # Workout
            "workout_evaluation": entry.workout_evaluation,
        }

        # Past performance features
        if horse_results:
            positions = [r.position for r in horse_results if r.position]
            last_3f_times = [r.last_3f for r in horse_results if r.last_3f]

            features["avg_position_last5"] = (
                sum(positions[:5]) / len(positions[:5]) if positions else None
            )
            features["win_rate"] = (
                sum(1 for p in positions if p == 1) / len(positions)
                if positions else 0
            )
            features["place_rate"] = (
                sum(1 for p in positions if p and p <= 3) / len(positions)
                if positions else 0
            )
            features["avg_last_3f"] = (
                sum(last_3f_times) / len(last_3f_times) if last_3f_times else None
            )
            features["best_last_3f"] = min(last_3f_times) if last_3f_times else None

            # Days since last race
            if horse_results[0].race:
                last_race_date = horse_results[0].race.date
                features["days_since_last_race"] = (race_date - last_race_date).days

        # Jockey features
        if entry.jockey:
            features["jockey_win_rate"] = entry.jockey.win_rate
            features["jockey_venue_win_rate"] = entry.jockey.venue_win_rate

        # Aptitude features (適性特徴量)
        race_distance = entry.race.distance if entry.race else None
        race_venue = entry.race.venue if entry.race else None
        race_track_condition = entry.race.track_condition if entry.race else None

        # Same distance results (同距離成績 ±200m)
        if race_distance:
            same_distance_results = await self.result_repo.get_by_horse_with_conditions(
                entry.horse_id, distance=race_distance, limit=20
            )
            if same_distance_results:
                positions = [r.position for r in same_distance_results if r.position]
                if positions:
                    features["same_distance_win_rate"] = sum(1 for p in positions if p == 1) / len(positions)
                    features["same_distance_place_rate"] = sum(1 for p in positions if p <= 3) / len(positions)

        # Same venue results (同コース成績)
        if race_venue:
            same_venue_results = await self.result_repo.get_by_horse_with_conditions(
                entry.horse_id, venue=race_venue, limit=20
            )
            if same_venue_results:
                positions = [r.position for r in same_venue_results if r.position]
                if positions:
                    features["same_venue_win_rate"] = sum(1 for p in positions if p == 1) / len(positions)
                    features["same_venue_place_rate"] = sum(1 for p in positions if p <= 3) / len(positions)

        # Same track condition results (同馬場状態成績)
        if race_track_condition:
            same_track_results = await self.result_repo.get_by_horse_with_conditions(
                entry.horse_id, track_condition=race_track_condition, limit=20
            )
            if same_track_results:
                positions = [r.position for r in same_track_results if r.position]
                if positions:
                    features["same_track_condition_place_rate"] = sum(1 for p in positions if p <= 3) / len(positions)

        return features

    async def build_features_for_race(self, race_id: int) -> pd.DataFrame | None:
        """Build features for all entries in a race."""
        from app.repositories import RaceRepository

        race_repo = RaceRepository(self.session)
        race = await race_repo.get_with_entries(race_id)
        if not race:
            return None

        entries = await self.entry_repo.get_by_race(race_id)
        if not entries:
            return None

        # Count running styles for pace prediction features
        escape_count = sum(1 for e in entries if e.running_style == "ESCAPE")
        front_count = sum(1 for e in entries if e.running_style == "FRONT")

        features_list = []
        for entry in entries:
            features = await self.build_features_for_entry(entry.id, race.date)
            if features:
                features["escape_horse_count"] = escape_count
                features["front_horse_count"] = front_count
                features["entry_id"] = entry.id
                features["horse_id"] = entry.horse_id
                features_list.append(features)

        if not features_list:
            return None

        return pd.DataFrame(features_list)

    async def build_training_data(
        self,
        race_ids: list[int],
    ) -> pd.DataFrame | None:
        """Build training data from historical races."""
        all_data = []

        for race_id in race_ids:
            features_df = await self.build_features_for_race(race_id)
            if features_df is None:
                continue

            # Get actual results
            results = await self.result_repo.get_by_race(race_id)
            result_map = {r.horse_id: r.position for r in results}

            # Add target variable
            features_df["position"] = features_df["horse_id"].map(result_map)
            features_df["is_place"] = features_df["position"].apply(
                lambda x: 1 if x and x <= 3 else 0
            )
            features_df["race_id"] = race_id

            all_data.append(features_df)

        if not all_data:
            return None

        return pd.concat(all_data, ignore_index=True)
