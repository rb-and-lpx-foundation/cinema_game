"""Tests for fuzzy actor name matching against cast lists."""

import pytest

from cinema_game_backend.matching import find_actor_in_cast


class TestExactMatch:
    def test_exact_full_name(self, departed_cast):
        result = find_actor_in_cast("Leonardo DiCaprio", departed_cast)
        assert result is not None
        assert result.matched_name == "Leonardo DiCaprio"

    def test_both_actors_found(self, departed_cast):
        assert find_actor_in_cast("Leonardo DiCaprio", departed_cast) is not None
        assert find_actor_in_cast("Matt Damon", departed_cast) is not None

    def test_case_insensitive(self, departed_cast):
        result = find_actor_in_cast("leonardo dicaprio", departed_cast)
        assert result is not None
        assert result.matched_name == "Leonardo DiCaprio"


class TestMisspelling:
    def test_minor_typo(self, departed_cast):
        result = find_actor_in_cast("Matt Daimon", departed_cast)
        assert result is not None
        assert result.matched_name == "Matt Damon"

    def test_shortened_first_name_not_matched(self, departed_cast):
        # "Leo" is a truncation of "Leonardo" — WRatio scores below _MIN_SCORE (82.8).
        # Tunable via _MIN_SCORE if the design team wants to accept truncations.
        result = find_actor_in_cast("Leo DiCaprio", departed_cast)
        assert result is None


class TestNotInCast:
    def test_actor_not_present(self, departed_cast):
        result = find_actor_in_cast("Tom Hanks", departed_cast)
        assert result is None

    def test_completely_unrelated(self, toy_story_cast):
        result = find_actor_in_cast("Leonardo DiCaprio", toy_story_cast)
        assert result is None

    def test_similar_first_name_different_person(self, departed_cast):
        # Should not match Mark Wahlberg or Matt Damon
        result = find_actor_in_cast("Mark Damon", departed_cast)
        assert result is None


class TestLastNameOnly:
    def test_unique_last_name(self, departed_cast):
        result = find_actor_in_cast("DiCaprio", departed_cast)
        assert result is not None
        assert result.matched_name == "Leonardo DiCaprio"

    def test_unique_last_name_nicholson(self, departed_cast):
        result = find_actor_in_cast("Nicholson", departed_cast)
        assert result is not None
        assert result.matched_name == "Jack Nicholson"


class TestNameVariant:
    def test_nickname_not_matched(self, apocalypse_now_cast):
        # Nicknames (Larry -> Laurence, Dick -> Richard, Bill -> William) have
        # large edit distances and are not handled by fuzzy string matching.
        # Tunable via max_distance or _MIN_SCORE if the design team wants to
        # add nickname support (e.g. a lookup table).
        result = find_actor_in_cast("Larry Fishburne", apocalypse_now_cast)
        assert result is None


class TestThreshold:
    # Uses Jack Nicholson misspellings at distances 1, 2, and 3:
    #   "Jack Nicholsen"  -> distance 1 (o -> e)
    #   "Jack Nickelson"  -> distance 2 (ho -> ke)
    #   "Jack Nickleson"  -> distance 3 (hol -> kle)

    def test_distance_1_within_threshold_1(self, departed_cast):
        result = find_actor_in_cast("Jack Nicholsen", departed_cast, max_distance=1)
        assert result is not None
        assert result.matched_name == "Jack Nicholson"

    def test_distance_2_rejected_by_threshold_1(self, departed_cast):
        result = find_actor_in_cast("Jack Nickelson", departed_cast, max_distance=1)
        assert result is None

    def test_distance_2_within_threshold_2(self, departed_cast):
        result = find_actor_in_cast("Jack Nickelson", departed_cast, max_distance=2)
        assert result is not None
        assert result.matched_name == "Jack Nicholson"

    def test_distance_3_rejected_by_threshold_2(self, departed_cast):
        result = find_actor_in_cast("Jack Nickleson", departed_cast, max_distance=2)
        assert result is None

    def test_distance_3_within_threshold_3(self, departed_cast):
        result = find_actor_in_cast("Jack Nickleson", departed_cast, max_distance=3)
        assert result is not None
        assert result.matched_name == "Jack Nicholson"

    def test_exact_rejected_by_threshold_0(self, departed_cast):
        # Distance 0 threshold only accepts exact matches
        result = find_actor_in_cast("Jack Nicholsen", departed_cast, max_distance=0)
        assert result is None


class TestEdgeCases:
    def test_empty_cast(self):
        result = find_actor_in_cast("Tom Hanks", [])
        assert result is None

    def test_empty_query(self, departed_cast):
        result = find_actor_in_cast("", departed_cast)
        assert result is None

    def test_whitespace_handling(self, departed_cast):
        result = find_actor_in_cast("  Matt   Damon  ", departed_cast)
        assert result is not None
        assert result.matched_name == "Matt Damon"
