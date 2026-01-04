"""Tests for simulation service."""

import pytest

from app.ml.pace import PaceResult
from app.models import RaceEntry, RunningStyle
from app.services.simulation_service import SimulationService


class TestSimulationService:
    """Tests for SimulationService operations."""

    @pytest.mark.asyncio
    async def test_generate_simulation(
        self, db_session, test_race, test_entries
    ):
        """Generate simulation returns RaceSimulation."""
        service = SimulationService(db_session)

        simulation = await service.generate_simulation(test_race.id)

        assert simulation is not None
        assert simulation.race_id == test_race.id
        assert simulation.race_name == test_race.name
        assert simulation.distance == test_race.distance
        assert simulation.predicted_pace in ["slow", "middle", "high"]

    @pytest.mark.asyncio
    async def test_generate_simulation_nonexistent(self, db_session):
        """Generate simulation for non-existent race returns None."""
        service = SimulationService(db_session)

        simulation = await service.generate_simulation(99999)

        assert simulation is None

    @pytest.mark.asyncio
    async def test_generate_simulation_no_entries(
        self, db_session, test_race
    ):
        """Generate simulation for race with no entries returns None."""
        service = SimulationService(db_session)

        simulation = await service.generate_simulation(test_race.id)

        assert simulation is None

    @pytest.mark.asyncio
    async def test_generate_simulation_includes_corner_positions(
        self, db_session, test_race, test_entries
    ):
        """Simulation includes corner positions."""
        service = SimulationService(db_session)

        simulation = await service.generate_simulation(test_race.id)

        assert simulation is not None
        assert simulation.corner_positions is not None
        assert len(simulation.corner_positions) == 5  # 1C, 2C, 3C, 4C, goal
        for corner in simulation.corner_positions:
            assert corner.corner_name in ["1C", "2C", "3C", "4C", "goal"]
            assert len(corner.horses) > 0

    @pytest.mark.asyncio
    async def test_generate_simulation_includes_start_formation(
        self, db_session, test_race, test_entries
    ):
        """Simulation includes start formation."""
        service = SimulationService(db_session)

        simulation = await service.generate_simulation(test_race.id)

        assert simulation is not None
        assert simulation.start_formation is not None
        assert simulation.start_formation.total_horses == len(test_entries)
        assert len(simulation.start_formation.rows) > 0

    @pytest.mark.asyncio
    async def test_generate_simulation_includes_scenarios(
        self, db_session, test_race, test_entries
    ):
        """Simulation includes pace scenarios."""
        service = SimulationService(db_session)

        simulation = await service.generate_simulation(test_race.id)

        assert simulation is not None
        assert simulation.scenarios is not None
        assert len(simulation.scenarios) == 3  # high, middle, slow

        pace_types = {s.pace_type for s in simulation.scenarios}
        assert pace_types == {"high", "middle", "slow"}

        for scenario in simulation.scenarios:
            assert scenario.probability > 0
            assert len(scenario.rankings) <= 5

    @pytest.mark.asyncio
    async def test_generate_simulation_includes_track_conditions(
        self, db_session, test_race, test_entries
    ):
        """Simulation includes track condition scenarios."""
        service = SimulationService(db_session)

        simulation = await service.generate_simulation(test_race.id)

        assert simulation is not None
        assert simulation.track_condition_scenarios is not None
        assert len(simulation.track_condition_scenarios) == 4  # 良, 稍重, 重, 不良

        conditions = {s.track_condition for s in simulation.track_condition_scenarios}
        assert conditions == {"良", "稍重", "重", "不良"}

    @pytest.mark.asyncio
    async def test_generate_simulation_includes_animation_frames(
        self, db_session, test_race, test_entries
    ):
        """Simulation includes animation frames."""
        service = SimulationService(db_session)

        simulation = await service.generate_simulation(test_race.id)

        assert simulation is not None
        assert simulation.animation_frames is not None
        assert len(simulation.animation_frames) == 61  # 60 frames + initial


class TestGenerateStartFormation:
    """Tests for _generate_start_formation method."""

    @pytest.mark.asyncio
    async def test_groups_by_running_style(
        self, db_session, test_race, test_entries
    ):
        """Start formation groups horses by running style."""
        service = SimulationService(db_session)

        entries = await service.entry_repo.get_by_race(test_race.id)
        formation = service._generate_start_formation(entries)

        assert formation.total_horses == len(entries)
        assert len(formation.rows) > 0

        # Check that row labels are appropriate
        valid_labels = {"先頭", "先行", "中団", "後方"}
        for row in formation.rows:
            assert row.row_label in valid_labels

    @pytest.mark.asyncio
    async def test_escape_horses_at_front(
        self, db_session, test_race, test_entries
    ):
        """Escape horses are in the first row."""
        service = SimulationService(db_session)

        entries = await service.entry_repo.get_by_race(test_race.id)
        formation = service._generate_start_formation(entries)

        # First row should be escape horses
        if formation.rows and formation.rows[0].row_label == "先頭":
            for horse in formation.rows[0].horses:
                assert horse.running_style == "ESCAPE"


class TestCalculateCornerPositions:
    """Tests for _calculate_corner_positions method."""

    @pytest.mark.asyncio
    async def test_positions_for_all_corners(
        self, db_session, test_race, test_entries
    ):
        """Calculates positions for all corners."""
        service = SimulationService(db_session)

        entries = await service.entry_repo.get_by_race(test_race.id)
        running_styles = [e.running_style for e in entries]

        pace_result = PaceResult(
            pace_type="middle",
            confidence=0.7,
            reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=2,
            front_count=3,
            stalker_count=4,
            closer_count=3,
        )

        race = await service.race_repo.get_with_entries(test_race.id)
        positions = service._calculate_corner_positions(entries, pace_result, race)

        assert len(positions) == 5
        corner_names = [p.corner_name for p in positions]
        assert corner_names == ["1C", "2C", "3C", "4C", "goal"]

    @pytest.mark.asyncio
    async def test_positions_have_correct_structure(
        self, db_session, test_race, test_entries
    ):
        """Corner positions have correct structure."""
        service = SimulationService(db_session)

        entries = await service.entry_repo.get_by_race(test_race.id)
        pace_result = PaceResult(
            pace_type="middle",
            confidence=0.7,
            reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=2,
            front_count=3,
            stalker_count=4,
            closer_count=3,
        )

        race = await service.race_repo.get_with_entries(test_race.id)
        positions = service._calculate_corner_positions(entries, pace_result, race)

        for corner in positions:
            assert len(corner.horses) == len(test_entries)
            for horse_pos in corner.horses:
                assert horse_pos.horse_number > 0
                assert horse_pos.horse_name is not None
                assert horse_pos.position >= 1
                assert horse_pos.distance_from_leader >= 0


class TestSimulateScenarios:
    """Tests for _simulate_scenarios method."""

    @pytest.mark.asyncio
    async def test_returns_three_scenarios(
        self, db_session, test_race, test_entries
    ):
        """Returns high, middle, and slow pace scenarios."""
        service = SimulationService(db_session)

        entries = await service.entry_repo.get_by_race(test_race.id)
        pace_result = PaceResult(
            pace_type="middle",
            confidence=0.7,
            reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=2,
            front_count=3,
            stalker_count=4,
            closer_count=3,
        )

        race = await service.race_repo.get_with_entries(test_race.id)
        scenarios = service._simulate_scenarios(entries, pace_result, race)

        assert len(scenarios) == 3
        pace_types = {s.pace_type for s in scenarios}
        assert pace_types == {"high", "middle", "slow"}

    @pytest.mark.asyncio
    async def test_scenarios_have_probabilities(
        self, db_session, test_race, test_entries
    ):
        """Each scenario has a probability."""
        service = SimulationService(db_session)

        entries = await service.entry_repo.get_by_race(test_race.id)
        pace_result = PaceResult(
            pace_type="middle",
            confidence=0.7,
            reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=2,
            front_count=3,
            stalker_count=4,
            closer_count=3,
        )

        race = await service.race_repo.get_with_entries(test_race.id)
        scenarios = service._simulate_scenarios(entries, pace_result, race)

        total_prob = sum(s.probability for s in scenarios)
        assert 0.99 <= total_prob <= 1.01  # Allow small floating point errors

    @pytest.mark.asyncio
    async def test_high_pace_prediction_biases_probabilities(
        self, db_session, test_race, test_entries
    ):
        """High pace prediction gives high probability to high scenario."""
        service = SimulationService(db_session)

        entries = await service.entry_repo.get_by_race(test_race.id)
        pace_result = PaceResult(
            pace_type="high",
            confidence=0.8,
            reason="test",
            advantageous_styles=["STALKER", "CLOSER"],
            escape_count=3,
            front_count=3,
            stalker_count=2,
            closer_count=2,
        )

        race = await service.race_repo.get_with_entries(test_race.id)
        scenarios = service._simulate_scenarios(entries, pace_result, race)

        high_scenario = next(s for s in scenarios if s.pace_type == "high")
        assert high_scenario.probability >= 0.5


class TestSimulateTrackConditions:
    """Tests for _simulate_track_conditions method."""

    @pytest.mark.asyncio
    async def test_returns_four_conditions(
        self, db_session, test_race, test_entries
    ):
        """Returns all four track conditions."""
        service = SimulationService(db_session)

        entries = await service.entry_repo.get_by_race(test_race.id)
        race = await service.race_repo.get_with_entries(test_race.id)

        results = service._simulate_track_conditions(entries, race)

        assert len(results) == 4
        conditions = {r.track_condition for r in results}
        assert conditions == {"良", "稍重", "重", "不良"}

    @pytest.mark.asyncio
    async def test_heavy_track_favors_front_runners(
        self, db_session, test_race, test_entries
    ):
        """Heavy track typically favors front runners."""
        service = SimulationService(db_session)

        entries = await service.entry_repo.get_by_race(test_race.id)
        race = await service.race_repo.get_with_entries(test_race.id)

        results = service._simulate_track_conditions(entries, race)

        heavy_result = next(r for r in results if r.track_condition == "重")
        # Heavy track should have positive front advantage
        assert heavy_result.front_advantage > 0


class TestInterpolateValue:
    """Tests for _interpolate_value method."""

    def test_interpolate_at_start(self, db_session):
        """Interpolate at progress 0."""
        service = SimulationService(db_session)

        positions = [(0.0, 5.0, 3), (0.5, 3.0, 2), (1.0, 1.0, 1)]
        value = service._interpolate_value(positions, 0.0, 1)

        assert value == 5.0

    def test_interpolate_at_end(self, db_session):
        """Interpolate at progress 1."""
        service = SimulationService(db_session)

        positions = [(0.0, 5.0, 3), (0.5, 3.0, 2), (1.0, 1.0, 1)]
        value = service._interpolate_value(positions, 1.0, 1)

        assert value == 1.0

    def test_interpolate_midpoint(self, db_session):
        """Interpolate at midpoint."""
        service = SimulationService(db_session)

        positions = [(0.0, 10.0, 3), (1.0, 0.0, 1)]
        value = service._interpolate_value(positions, 0.5, 1)

        assert value == 5.0

    def test_interpolate_empty_positions(self, db_session):
        """Empty positions returns 0."""
        service = SimulationService(db_session)

        value = service._interpolate_value([], 0.5, 1)

        assert value == 0.0


class TestGenerateAnimationFrames:
    """Tests for _generate_animation_frames method."""

    @pytest.mark.asyncio
    async def test_generates_61_frames(
        self, db_session, test_race, test_entries
    ):
        """Generates 61 frames (0-60 inclusive)."""
        service = SimulationService(db_session)

        entries = await service.entry_repo.get_by_race(test_race.id)
        pace_result = PaceResult(
            pace_type="middle",
            confidence=0.7,
            reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=2,
            front_count=3,
            stalker_count=4,
            closer_count=3,
        )

        race = await service.race_repo.get_with_entries(test_race.id)
        corner_positions = service._calculate_corner_positions(entries, pace_result, race)
        frames = service._generate_animation_frames(entries, corner_positions)

        assert len(frames) == 61

    @pytest.mark.asyncio
    async def test_frames_have_all_horses(
        self, db_session, test_race, test_entries
    ):
        """Each frame includes all horses."""
        service = SimulationService(db_session)

        entries = await service.entry_repo.get_by_race(test_race.id)
        pace_result = PaceResult(
            pace_type="middle",
            confidence=0.7,
            reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=2,
            front_count=3,
            stalker_count=4,
            closer_count=3,
        )

        race = await service.race_repo.get_with_entries(test_race.id)
        corner_positions = service._calculate_corner_positions(entries, pace_result, race)
        frames = service._generate_animation_frames(entries, corner_positions)

        for frame in frames:
            assert len(frame.horses) == len(test_entries)

    @pytest.mark.asyncio
    async def test_frames_progress_increases(
        self, db_session, test_race, test_entries
    ):
        """Frame progress increases over time."""
        service = SimulationService(db_session)

        entries = await service.entry_repo.get_by_race(test_race.id)
        pace_result = PaceResult(
            pace_type="middle",
            confidence=0.7,
            reason="test",
            advantageous_styles=["FRONT", "STALKER"],
            escape_count=2,
            front_count=3,
            stalker_count=4,
            closer_count=3,
        )

        race = await service.race_repo.get_with_entries(test_race.id)
        corner_positions = service._calculate_corner_positions(entries, pace_result, race)
        frames = service._generate_animation_frames(entries, corner_positions)

        # First frame should be near 0
        assert frames[0].time < 0.1
        # Last frame should be near 1
        assert frames[-1].time > 0.9
