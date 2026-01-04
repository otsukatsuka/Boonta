"""Tests for entry repository."""

import pytest

from app.repositories.entry_repository import EntryRepository


class TestEntryRepository:
    """Tests for EntryRepository specialized queries."""

    @pytest.mark.asyncio
    async def test_get_by_race(self, db_session, test_race, test_entries):
        """Get all entries for a race."""
        repo = EntryRepository(db_session)

        entries = await repo.get_by_race(test_race.id)

        assert len(entries) == len(test_entries)
        # Entries should be ordered by horse_number
        for i, entry in enumerate(entries):
            assert entry.horse_number == i + 1
            # Check that horse and jockey are loaded
            assert entry.horse is not None
            if entry.jockey_id:
                assert entry.jockey is not None

    @pytest.mark.asyncio
    async def test_get_by_race_empty(self, db_session, test_race):
        """Get entries for race with no entries returns empty list."""
        repo = EntryRepository(db_session)

        entries = await repo.get_by_race(test_race.id)

        assert entries == []

    @pytest.mark.asyncio
    async def test_get_by_race_nonexistent(self, db_session):
        """Get entries for non-existent race returns empty list."""
        repo = EntryRepository(db_session)

        entries = await repo.get_by_race(99999)

        assert entries == []

    @pytest.mark.asyncio
    async def test_get_by_race_and_horse(
        self, db_session, test_race, test_entries, test_horses
    ):
        """Get specific entry by race and horse."""
        repo = EntryRepository(db_session)

        entry = await repo.get_by_race_and_horse(test_race.id, test_horses[0].id)

        assert entry is not None
        assert entry.race_id == test_race.id
        assert entry.horse_id == test_horses[0].id

    @pytest.mark.asyncio
    async def test_get_by_race_and_horse_nonexistent(
        self, db_session, test_race, test_entries
    ):
        """Get entry with non-existent horse returns None."""
        repo = EntryRepository(db_session)

        entry = await repo.get_by_race_and_horse(test_race.id, 99999)

        assert entry is None

    @pytest.mark.asyncio
    async def test_get_with_relations(
        self, db_session, test_race, test_entries
    ):
        """Get entry with all relations loaded."""
        repo = EntryRepository(db_session)

        entry = await repo.get_with_relations(test_entries[0].id)

        assert entry is not None
        assert entry.horse is not None
        assert entry.race is not None
        if entry.jockey_id:
            assert entry.jockey is not None

    @pytest.mark.asyncio
    async def test_get_with_relations_nonexistent(self, db_session):
        """Get entry with relations for non-existent entry returns None."""
        repo = EntryRepository(db_session)

        entry = await repo.get_with_relations(99999)

        assert entry is None

    @pytest.mark.asyncio
    async def test_update_workout(
        self, db_session, test_race, test_entries
    ):
        """Update workout information."""
        repo = EntryRepository(db_session)
        entry_id = test_entries[0].id

        updated = await repo.update_workout(
            entry_id,
            workout_time="1:12.5",
            workout_evaluation="A",
            workout_course="美浦坂路",
            workout_memo="好調子",
        )

        assert updated is not None
        assert updated.workout_time == "1:12.5"
        assert updated.workout_evaluation == "A"
        assert updated.workout_course == "美浦坂路"
        assert updated.workout_memo == "好調子"

    @pytest.mark.asyncio
    async def test_update_workout_partial(
        self, db_session, test_race, test_entries
    ):
        """Update workout with only some fields."""
        repo = EntryRepository(db_session)
        entry_id = test_entries[0].id

        updated = await repo.update_workout(
            entry_id,
            workout_evaluation="S",
        )

        assert updated is not None
        assert updated.workout_evaluation == "S"

    @pytest.mark.asyncio
    async def test_update_workout_nonexistent(self, db_session):
        """Update workout for non-existent entry returns None."""
        repo = EntryRepository(db_session)

        result = await repo.update_workout(99999, workout_evaluation="A")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_comment(
        self, db_session, test_race, test_entries
    ):
        """Update trainer comment."""
        repo = EntryRepository(db_session)
        entry_id = test_entries[0].id

        updated = await repo.update_comment(entry_id, "調子良好、勝負気配")

        assert updated is not None
        assert updated.trainer_comment == "調子良好、勝負気配"

    @pytest.mark.asyncio
    async def test_update_comment_none_preserves_value(
        self, db_session, test_race, test_entries
    ):
        """Passing None preserves existing comment (BaseRepository behavior)."""
        repo = EntryRepository(db_session)
        entry_id = test_entries[0].id

        # First set a comment
        await repo.update_comment(entry_id, "初期コメント")
        await db_session.flush()

        # Passing None should not change the value (BaseRepository skips None values)
        updated = await repo.update_comment(entry_id, None)

        assert updated is not None
        assert updated.trainer_comment == "初期コメント"

    @pytest.mark.asyncio
    async def test_update_comment_nonexistent(self, db_session):
        """Update comment for non-existent entry returns None."""
        repo = EntryRepository(db_session)

        result = await repo.update_comment(99999, "コメント")

        assert result is None
