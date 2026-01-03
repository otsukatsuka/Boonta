"""Simulation service for race visualization."""

import math
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.pace import predict_pace, get_pace_advantage_score, PaceResult, VENUE_CHARACTERISTICS, TRACK_CONDITION_EFFECTS
from app.models import RaceEntry
from app.repositories import EntryRepository, RaceRepository
from app.schemas.simulation import (
    AnimationFrame,
    AnimationHorse,
    CornerPositions,
    FormationHorse,
    FormationRow,
    HorsePosition,
    RaceSimulation,
    ScenarioKeyHorse,
    ScenarioRanking,
    ScenarioResult,
    StartFormation,
    TrackConditionResult,
)


# Running style to expected first corner position
STYLE_TO_CORNER_POSITION = {
    "ESCAPE": 1.5,
    "FRONT": 4.0,
    "STALKER": 7.0,
    "CLOSER": 12.0,
    "VERSATILE": 8.0,
}

# Pace type labels in Japanese
PACE_LABELS = {
    "slow": "スローペース",
    "middle": "ミドルペース",
    "high": "ハイペース",
}


class SimulationService:
    """Service for generating race simulations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.race_repo = RaceRepository(session)
        self.entry_repo = EntryRepository(session)

    async def generate_simulation(self, race_id: int) -> RaceSimulation | None:
        """Generate race simulation data for visualization."""
        race = await self.race_repo.get_with_entries(race_id)
        if not race:
            return None

        entries = await self.entry_repo.get_by_race(race_id)
        if not entries:
            return None

        # Get running styles and escape horse popularities
        running_styles = [e.running_style for e in entries]
        escape_popularities = [
            e.popularity for e in entries
            if e.running_style == "ESCAPE" and e.popularity
        ]

        # Predict pace with venue and track condition
        pace_result = predict_pace(
            running_styles,
            distance=race.distance,
            course_type=race.course_type or "芝",
            venue=race.venue,
            track_condition=race.track_condition,
            escape_popularities=escape_popularities if escape_popularities else None,
        )

        # Get venue description
        venue_char = VENUE_CHARACTERISTICS.get(race.venue or "", {})
        venue_description = venue_char.get("description", "")
        if race.track_condition and race.track_condition != "良":
            track_effect = TRACK_CONDITION_EFFECTS.get(race.track_condition, {})
            track_desc = track_effect.get("description", "")
            if track_desc:
                venue_description += f" / {race.track_condition}馬場: {track_desc}"

        # Generate simulation components
        start_formation = self._generate_start_formation(entries)
        corner_positions = self._calculate_corner_positions(entries, pace_result, race)
        scenarios = self._simulate_scenarios(entries, pace_result, race)
        track_condition_scenarios = self._simulate_track_conditions(entries, race)
        animation_frames = self._generate_animation_frames(entries, corner_positions)

        return RaceSimulation(
            race_id=race_id,
            race_name=race.name,
            distance=race.distance,
            course_type=race.course_type or "芝",
            venue=race.venue,
            track_condition=race.track_condition,
            venue_description=venue_description if venue_description else None,
            corner_positions=corner_positions,
            start_formation=start_formation,
            scenarios=scenarios,
            track_condition_scenarios=track_condition_scenarios,
            predicted_pace=pace_result.pace_type,
            animation_frames=animation_frames,
        )

    def _generate_start_formation(self, entries: list[RaceEntry]) -> StartFormation:
        """Generate start formation diagram based on running styles."""
        # Group horses by running style
        style_groups: dict[str, list[FormationHorse]] = {
            "ESCAPE": [],
            "FRONT": [],
            "STALKER": [],
            "CLOSER": [],
            "VERSATILE": [],
        }

        for entry in entries:
            if not entry.horse:
                continue
            style = entry.running_style or "VERSATILE"
            horse = FormationHorse(
                horse_number=entry.horse_number or 0,
                horse_name=entry.horse.name,
                running_style=style,
            )
            if style in style_groups:
                style_groups[style].append(horse)

        # Build formation rows
        rows = []
        row_index = 0

        # Row 0: Escape horses (front)
        if style_groups["ESCAPE"]:
            rows.append(FormationRow(
                row_index=row_index,
                row_label="先頭",
                horses=style_groups["ESCAPE"],
            ))
            row_index += 1

        # Row 1-2: Front runners
        front_horses = style_groups["FRONT"]
        if front_horses:
            # Split into two rows if more than 4
            if len(front_horses) <= 4:
                rows.append(FormationRow(
                    row_index=row_index,
                    row_label="先行",
                    horses=front_horses,
                ))
                row_index += 1
            else:
                mid = len(front_horses) // 2
                rows.append(FormationRow(
                    row_index=row_index,
                    row_label="先行",
                    horses=front_horses[:mid],
                ))
                row_index += 1
                rows.append(FormationRow(
                    row_index=row_index,
                    row_label="先行",
                    horses=front_horses[mid:],
                ))
                row_index += 1

        # Row 3-4: Stalkers (middle group)
        stalkers = style_groups["STALKER"] + style_groups["VERSATILE"]
        if stalkers:
            if len(stalkers) <= 4:
                rows.append(FormationRow(
                    row_index=row_index,
                    row_label="中団",
                    horses=stalkers,
                ))
                row_index += 1
            else:
                mid = len(stalkers) // 2
                rows.append(FormationRow(
                    row_index=row_index,
                    row_label="中団",
                    horses=stalkers[:mid],
                ))
                row_index += 1
                rows.append(FormationRow(
                    row_index=row_index,
                    row_label="中団",
                    horses=stalkers[mid:],
                ))
                row_index += 1

        # Row 5+: Closers (back)
        if style_groups["CLOSER"]:
            rows.append(FormationRow(
                row_index=row_index,
                row_label="後方",
                horses=style_groups["CLOSER"],
            ))

        return StartFormation(
            rows=rows,
            total_horses=len(entries),
        )

    def _calculate_corner_positions(
        self,
        entries: list[RaceEntry],
        pace_result: PaceResult,
        race=None,
    ) -> list[CornerPositions]:
        """Calculate horse positions at each corner."""
        corners = ["1C", "2C", "3C", "4C", "goal"]
        all_positions = []

        # Calculate initial positions based on running style
        horses_data = []
        for entry in entries:
            if not entry.horse:
                continue
            style = entry.running_style or "VERSATILE"
            base_position = STYLE_TO_CORNER_POSITION.get(style, 8.0)
            # Add some randomness based on horse number
            jitter = (entry.horse_number or 0) * 0.1 % 1.0
            horses_data.append({
                "horse_number": entry.horse_number or 0,
                "horse_name": entry.horse.name,
                "running_style": style,
                "base_position": base_position + jitter,
                "odds": entry.odds or 50.0,
                "popularity": entry.popularity or 10,
            })

        for corner_idx, corner_name in enumerate(corners):
            positions = []
            progress = corner_idx / (len(corners) - 1)  # 0 to 1

            for horse in horses_data:
                style = horse["running_style"]
                base = horse["base_position"]

                # Position changes based on corner and pace
                if corner_name == "1C":
                    # First corner - mostly based on running style
                    position = base
                elif corner_name == "2C":
                    # Second corner - slight adjustment
                    position = base * 0.95
                elif corner_name == "3C":
                    # Third corner - stalkers start moving up
                    if style in ["STALKER", "VERSATILE"]:
                        position = base * 0.8
                    elif style == "CLOSER":
                        position = base * 0.9
                    else:
                        position = base
                elif corner_name == "4C":
                    # Fourth corner - big moves happen
                    if pace_result.pace_type == "high":
                        # High pace - closers gain ground
                        if style in ["STALKER", "CLOSER"]:
                            position = base * 0.6
                        else:
                            position = base * 1.2  # Front runners tire
                    elif pace_result.pace_type == "slow":
                        # Slow pace - front runners hold
                        if style in ["ESCAPE", "FRONT"]:
                            position = base * 0.9
                        else:
                            position = base * 0.95
                    else:
                        position = base * 0.85
                else:
                    # Goal - final positions based on pace advantage
                    advantage = get_pace_advantage_score(style, pace_result)
                    # Lower odds = better final position
                    odds_factor = 1.0 / (1.0 + math.log(horse["odds"] + 1) / 5.0)
                    position = base * (0.7 / advantage) * (1.0 / odds_factor)

                positions.append({
                    "horse": horse,
                    "position": position,
                })

            # Sort by position and assign ranks
            positions.sort(key=lambda x: x["position"])
            horse_positions = []
            for rank, p in enumerate(positions, 1):
                h = p["horse"]
                distance = (rank - 1) * 0.5  # 0.5 horse lengths between positions
                horse_positions.append(HorsePosition(
                    horse_number=h["horse_number"],
                    horse_name=h["horse_name"],
                    running_style=h["running_style"],
                    position=rank,
                    distance_from_leader=distance,
                ))

            all_positions.append(CornerPositions(
                corner_name=corner_name,
                horses=horse_positions,
            ))

        return all_positions

    def _simulate_scenarios(
        self,
        entries: list[RaceEntry],
        base_pace: PaceResult,
        race=None,
    ) -> list[ScenarioResult]:
        """Simulate results for different pace scenarios."""
        scenarios = []
        running_styles = [e.running_style for e in entries]

        # Get venue and track condition info
        venue = race.venue if race else None
        track_condition = race.track_condition if race else "良"
        venue_char = VENUE_CHARACTERISTICS.get(venue or "", {})
        front_advantage = venue_char.get("front_advantage", 0.0)
        track_effect = TRACK_CONDITION_EFFECTS.get(track_condition or "良", {})
        front_mod = track_effect.get("front_modifier", 0.0)
        total_front_advantage = front_advantage + front_mod

        # Define scenario probabilities based on base prediction
        if base_pace.pace_type == "high":
            probabilities = {"high": 0.6, "middle": 0.3, "slow": 0.1}
        elif base_pace.pace_type == "slow":
            probabilities = {"high": 0.1, "middle": 0.3, "slow": 0.6}
        else:
            probabilities = {"high": 0.25, "middle": 0.5, "slow": 0.25}

        for pace_type in ["high", "middle", "slow"]:
            # Create pace result for this scenario with venue/track consideration
            if pace_type == "high":
                advantageous = ["STALKER", "CLOSER"]
                description = "激しい先行争いで差し・追込有利"
                if total_front_advantage >= 0.15:
                    description += f"（ただし{venue}は前残り傾向）"
            elif pace_type == "slow":
                advantageous = ["ESCAPE", "FRONT"]
                description = "スローペースで前残り警戒"
                if total_front_advantage >= 0.15:
                    description += f"（{venue}の前有利で逃げ切り濃厚）"
                elif total_front_advantage <= -0.10:
                    description += f"（{venue}は差し有利なので注意）"
            else:
                advantageous = ["FRONT", "STALKER"]
                description = "平均ペースで実力通りの決着"

            # Add track condition note
            if track_condition and track_condition != "良":
                description += f"【{track_condition}馬場】"

            scenario_pace = PaceResult(
                pace_type=pace_type,
                confidence=0.5,
                reason="",
                advantageous_styles=advantageous,
                escape_count=base_pace.escape_count,
                front_count=base_pace.front_count,
                stalker_count=base_pace.stalker_count,
                closer_count=base_pace.closer_count,
            )

            # Calculate scores for each horse
            horse_scores = []
            for entry in entries:
                if not entry.horse:
                    continue
                style = entry.running_style or "VERSATILE"
                advantage = get_pace_advantage_score(style, scenario_pace)

                # Base score from odds
                odds = entry.odds or 50.0
                base_score = 1.0 / (1.0 + math.log(odds + 1))

                # Apply advantage
                score = base_score * advantage

                horse_scores.append({
                    "horse_number": entry.horse_number or 0,
                    "horse_name": entry.horse.name,
                    "running_style": style,
                    "score": score,
                    "popularity": entry.popularity or 10,
                })

            # Sort by score and get top 5
            horse_scores.sort(key=lambda x: x["score"], reverse=True)
            rankings = []
            key_horses = []

            for rank, h in enumerate(horse_scores[:5], 1):
                rankings.append(ScenarioRanking(
                    rank=rank,
                    horse_number=h["horse_number"],
                    horse_name=h["horse_name"],
                    score=min(h["score"], 1.0),
                ))

            # Find key horses (dark horses that benefit from this scenario)
            for h in horse_scores:
                if h["popularity"] >= 6 and h["running_style"] in advantageous:
                    key_horses.append(ScenarioKeyHorse(
                        horse_number=h["horse_number"],
                        horse_name=h["horse_name"],
                        reason=f"{PACE_LABELS[pace_type]}で展開向く",
                    ))
                    if len(key_horses) >= 2:
                        break

            scenarios.append(ScenarioResult(
                pace_type=pace_type,
                pace_label=PACE_LABELS[pace_type],
                probability=probabilities[pace_type],
                rankings=rankings,
                key_horses=key_horses,
                advantageous_styles=advantageous,
                description=description,
            ))

        return scenarios

    def _generate_animation_frames(
        self,
        entries: list[RaceEntry],
        corner_positions: list[CornerPositions],
    ) -> list[AnimationFrame]:
        """Generate animation frames for race visualization."""
        frame_count = 60  # 60 frames for smooth animation
        frames = []

        # Map corner to progress: 1C=0.2, 2C=0.4, 3C=0.6, 4C=0.8, goal=1.0
        corner_progress = {"1C": 0.2, "2C": 0.4, "3C": 0.6, "4C": 0.8, "goal": 1.0}

        # Build position data for interpolation
        position_data = {}  # horse_number -> [(progress, position, lane)]

        for corner in corner_positions:
            progress = corner_progress.get(corner.corner_name, 0.0)
            for horse in corner.horses:
                if horse.horse_number not in position_data:
                    position_data[horse.horse_number] = {
                        "name": horse.horse_name,
                        "style": horse.running_style,
                        "positions": [],
                    }
                # Lane based on position (inner lanes for front runners)
                lane = min(max(1, (horse.position - 1) // 2 + 1), 8)
                position_data[horse.horse_number]["positions"].append(
                    (progress, horse.position, lane)
                )

        # Add starting positions (progress=0)
        for horse_num, data in position_data.items():
            style = data["style"] or "VERSATILE"
            start_position = STYLE_TO_CORNER_POSITION.get(style, 8.0)
            start_lane = min(max(1, int(start_position) // 2 + 1), 8)
            data["positions"].insert(0, (0.0, start_position, start_lane))

        # Get total horses count for position offset calculation
        total_horses = len(position_data)

        # Generate frames
        for i in range(frame_count + 1):
            base_progress = i / frame_count
            horses = []

            for horse_num, data in position_data.items():
                # Interpolate position (rank) and lane
                positions = data["positions"]
                pos = self._interpolate_value(positions, base_progress, 1)
                lane = int(self._interpolate_value(positions, base_progress, 2))

                # Adjust progress based on position (rank)
                # Front runners are slightly ahead, back runners slightly behind
                # The offset grows as the race progresses (starts at 0, max at finish)
                # Position offset: 1st place = +0.06, last place = -0.06 (total spread = 12%)
                max_offset = 0.12 * (1 - (pos - 1) / max(total_horses - 1, 1)) - 0.06
                # Scale offset by race progress (no offset at start, full offset at finish)
                position_offset = max_offset * base_progress
                progress = max(0, min(1, base_progress + position_offset))

                horses.append(AnimationHorse(
                    horse_number=horse_num,
                    horse_name=data["name"],
                    running_style=data["style"],
                    progress=progress,
                    lane=min(max(1, lane), 8),
                ))

            frames.append(AnimationFrame(
                time=progress,
                horses=horses,
            ))

        return frames

    def _interpolate_value(
        self,
        positions: list[tuple[float, float, int]],
        progress: float,
        value_index: int,
    ) -> float:
        """Interpolate a value at given progress."""
        if not positions:
            return 0.0

        # Find the two nearest data points
        prev = positions[0]
        next_pos = positions[-1]

        for i, p in enumerate(positions):
            if p[0] <= progress:
                prev = p
            if p[0] >= progress:
                next_pos = p
                break

        if prev[0] == next_pos[0]:
            return float(prev[value_index])

        # Linear interpolation
        t = (progress - prev[0]) / (next_pos[0] - prev[0])
        return prev[value_index] + t * (next_pos[value_index] - prev[value_index])

    def _simulate_track_conditions(
        self,
        entries: list[RaceEntry],
        race=None,
    ) -> list[TrackConditionResult]:
        """Simulate results for different track conditions (良/稍重/重/不良)."""
        results = []
        running_styles = [e.running_style for e in entries]

        # Get venue front advantage
        venue = race.venue if race else None
        venue_char = VENUE_CHARACTERISTICS.get(venue or "", {})
        base_front_advantage = venue_char.get("front_advantage", 0.0)

        # Get escape horse popularities for pace prediction
        escape_popularities = [
            e.popularity for e in entries
            if e.running_style == "ESCAPE" and e.popularity
        ]

        track_conditions = ["良", "稍重", "重", "不良"]

        for condition in track_conditions:
            track_effect = TRACK_CONDITION_EFFECTS.get(condition, {})
            front_mod = track_effect.get("front_modifier", 0.0)
            total_front_advantage = base_front_advantage + front_mod
            track_desc = track_effect.get("description", "")

            # Predict pace for this track condition
            pace_result = predict_pace(
                running_styles,
                distance=race.distance if race else 2000,
                course_type=race.course_type if race else "芝",
                venue=venue,
                track_condition=condition,
                escape_popularities=escape_popularities if escape_popularities else None,
            )

            # Determine advantageous styles based on track and pace
            if total_front_advantage >= 0.2:
                advantageous = ["ESCAPE", "FRONT"]
                description = f"{condition}馬場: 前有利が強まる。逃げ・先行馬を重視"
            elif total_front_advantage >= 0.1:
                advantageous = ["FRONT", "ESCAPE"]
                description = f"{condition}馬場: やや前有利。先行馬に注目"
            elif total_front_advantage <= -0.05:
                advantageous = ["STALKER", "CLOSER"]
                description = f"{condition}馬場: 差し有利。末脚勝負"
            else:
                advantageous = pace_result.advantageous_styles
                description = f"{condition}馬場: {track_desc}" if track_desc else f"{condition}馬場"

            # Calculate scores for each horse
            horse_scores = []
            for entry in entries:
                if not entry.horse:
                    continue
                style = entry.running_style or "VERSATILE"

                # Base score from odds (reduced weight)
                odds = entry.odds or 50.0
                base_score = 1.0 / (1.0 + math.log(odds + 1))

                # Track condition advantage - STRONGER adjustments
                # 馬場状態による調整を大きくする
                if style in advantageous:
                    position = advantageous.index(style)
                    # 第1有利: +40%, 第2有利: +25%
                    advantage = 1.4 - (position * 0.15)
                else:
                    # Disadvantageous styles - STRONGER penalty
                    if style in ["ESCAPE", "FRONT"] and total_front_advantage < 0:
                        # 差し有利コースで前の馬は大きく不利
                        advantage = 0.65
                    elif style in ["STALKER", "CLOSER"] and total_front_advantage >= 0.2:
                        # 前有利コース（重馬場など）で差し馬は大きく不利
                        advantage = 0.60
                    elif style in ["STALKER", "CLOSER"] and total_front_advantage >= 0.1:
                        # やや前有利で差し馬はやや不利
                        advantage = 0.75
                    else:
                        advantage = 0.9

                # 馬場が悪いほど脚質の影響を大きくする
                if condition in ["重", "不良"]:
                    # 重・不良では脚質の差がより顕著に
                    if advantage > 1.0:
                        advantage = 1.0 + (advantage - 1.0) * 1.3  # ボーナス強化
                    else:
                        advantage = 1.0 - (1.0 - advantage) * 1.3  # ペナルティ強化

                score = base_score * advantage

                horse_scores.append({
                    "horse_number": entry.horse_number or 0,
                    "horse_name": entry.horse.name,
                    "running_style": style,
                    "score": score,
                    "popularity": entry.popularity or 10,
                })

            # Sort by score and get top 5
            horse_scores.sort(key=lambda x: x["score"], reverse=True)
            rankings = []
            key_horses = []

            for rank, h in enumerate(horse_scores[:5], 1):
                rankings.append(ScenarioRanking(
                    rank=rank,
                    horse_number=h["horse_number"],
                    horse_name=h["horse_name"],
                    score=min(h["score"], 1.0),
                ))

            # Find key horses (dark horses that benefit from this condition)
            for h in horse_scores:
                if h["popularity"] >= 6 and h["running_style"] in advantageous:
                    key_horses.append(ScenarioKeyHorse(
                        horse_number=h["horse_number"],
                        horse_name=h["horse_name"],
                        reason=f"{condition}馬場で有利",
                    ))
                    if len(key_horses) >= 2:
                        break

            results.append(TrackConditionResult(
                track_condition=condition,
                front_advantage=total_front_advantage,
                rankings=rankings,
                key_horses=key_horses,
                advantageous_styles=advantageous,
                description=description,
            ))

        return results
