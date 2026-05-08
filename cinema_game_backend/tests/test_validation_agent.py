"""Tests for validate_move using a mocked TMDbClient."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from art_graph.cinema_data_providers.tmdb_models import Movie, CastMember
from cinema_game_backend.agents.validation_agent import validate_move


def make_movie(
    title="Thor", movie_id=10195, release_date="2011-04-21", poster_path="/thor.jpg"
):
    return Movie(
        id=movie_id, title=title, release_date=release_date, poster_path=poster_path
    )


def make_cast(*names):
    return [CastMember(id=i + 1, name=n) for i, n in enumerate(names)]


@pytest.fixture
def thor_cast():
    return make_cast(
        "Chris Hemsworth",
        "Natalie Portman",
        "Tom Hiddleston",
        "Anthony Hopkins",
        "Kat Dennings",
        "Stellan Skarsgård",
        "Idris Elba",
        "Rene Russo",
    )


@pytest.fixture
def mock_tmdb(thor_cast):
    tmdb = AsyncMock()
    tmdb.search_movie.return_value = make_movie()
    tmdb.get_movie_cast.return_value = thor_cast
    return tmdb


class TestValidMove:
    async def test_both_actors_exact(self, mock_tmdb):
        result = await validate_move(
            mock_tmdb, "Chris Hemsworth", "Thor", "Natalie Portman"
        )
        assert result.valid is True
        assert result.from_actor_found is True
        assert result.to_actor_found is True
        assert result.movie_id == 10195
        assert result.movie_title == "Thor"

    async def test_minor_typo_accepted(self, mock_tmdb):
        result = await validate_move(
            mock_tmdb, "Chris Hemsworth", "Thor", "Natalie Portmen"
        )
        assert result.valid is True
        assert result.to_actor_found is True


class TestInvalidMove:
    async def test_actor_not_in_cast(self, mock_tmdb):
        result = await validate_move(
            mock_tmdb, "Chris Hemsworth", "Thor", "Leonardo DiCaprio"
        )
        assert result.valid is False
        assert result.from_actor_found is True
        assert result.to_actor_found is False
        assert "Leonardo DiCaprio" in result.explanation

    async def test_neither_actor_in_cast(self, mock_tmdb):
        result = await validate_move(
            mock_tmdb, "Brad Pitt", "Thor", "Leonardo DiCaprio"
        )
        assert result.valid is False
        assert result.from_actor_found is False
        assert result.to_actor_found is False

    async def test_movie_not_found(self, mock_tmdb):
        mock_tmdb.search_movie.return_value = None
        result = await validate_move(
            mock_tmdb, "Chris Hemsworth", "Nonexistent Movie", "Natalie Portman"
        )
        assert result.valid is False
        assert "not found" in result.explanation.lower()


class TestMisspelledFinalActor:
    """Regression tests for the bug where a misspelled final actor
    validates correctly but the game fails to detect completion."""

    async def test_misspelled_name_still_valid(self, mock_tmdb):
        # "Kat Denings" -> "Kat Dennings" (distance 1)
        result = await validate_move(
            mock_tmdb, "Chris Hemsworth", "Thor", "Kat Denings"
        )
        assert result.valid is True
        assert result.to_actor_found is True

    async def test_explanation_uses_canonical_name(self, mock_tmdb):
        result = await validate_move(
            mock_tmdb, "Chris Hemsworth", "Thor", "Kat Denings"
        )
        assert "Kat Dennings" in result.explanation

    async def test_to_actor_name_is_canonical(self, mock_tmdb):
        result = await validate_move(
            mock_tmdb, "Chris Hemsworth", "Thor", "Kat Denings"
        )
        assert result.to_actor_name == "Kat Dennings"

    async def test_from_actor_name_is_canonical(self, mock_tmdb):
        result = await validate_move(
            mock_tmdb, "Chris Hemswerth", "Thor", "Kat Dennings"
        )
        assert result.from_actor_name == "Chris Hemsworth"


class TestLLMFallback:
    """Tests for LLM fallback when fuzzy matching fails (e.g. nicknames)."""

    @pytest.fixture
    def apocalypse_now_tmdb(self):
        tmdb = AsyncMock()
        tmdb.search_movie.return_value = make_movie(
            title="Apocalypse Now",
            movie_id=28,
            release_date="1979-08-15",
            poster_path="/apocalypse.jpg",
        )
        tmdb.get_movie_cast.return_value = make_cast(
            "Marlon Brando",
            "Martin Sheen",
            "Robert Duvall",
            "Frederic Forrest",
            "Sam Bottoms",
            "Laurence Fishburne",
            "Dennis Hopper",
        )
        return tmdb

    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        llm.invoke_json.return_value = {"matched_name": "Laurence Fishburne"}
        return llm

    async def test_nickname_resolved_by_llm(self, apocalypse_now_tmdb, mock_llm):
        result = await validate_move(
            apocalypse_now_tmdb,
            "Marlon Brando",
            "Apocalypse Now",
            "Larry Fishburne",
            llm=mock_llm,
        )
        assert result.valid is True
        assert result.to_actor_found is True
        assert result.to_actor_name == "Laurence Fishburne"

    async def test_nickname_fails_without_llm(self, apocalypse_now_tmdb):
        result = await validate_move(
            apocalypse_now_tmdb,
            "Marlon Brando",
            "Apocalypse Now",
            "Larry Fishburne",
        )
        assert result.valid is False
        assert result.to_actor_found is False

    async def test_llm_returns_null_match(self, apocalypse_now_tmdb):
        llm = MagicMock()
        llm.invoke_json.return_value = {"matched_name": None}
        result = await validate_move(
            apocalypse_now_tmdb,
            "Marlon Brando",
            "Apocalypse Now",
            "Larry Fishburne",
            llm=llm,
        )
        assert result.valid is False
        assert result.to_actor_found is False

    async def test_llm_exception_degrades_gracefully(self, apocalypse_now_tmdb):
        llm = MagicMock()
        llm.invoke_json.side_effect = RuntimeError("API timeout")
        result = await validate_move(
            apocalypse_now_tmdb,
            "Marlon Brando",
            "Apocalypse Now",
            "Larry Fishburne",
            llm=llm,
        )
        assert result.valid is False
        assert result.to_actor_found is False

    async def test_llm_not_called_when_fuzzy_matches(
        self, apocalypse_now_tmdb, mock_llm
    ):
        result = await validate_move(
            apocalypse_now_tmdb,
            "Marlon Brando",
            "Apocalypse Now",
            "Laurence Fishburne",
            llm=mock_llm,
        )
        assert result.valid is True
        mock_llm.invoke_json.assert_not_called()


class TestMovieMetadata:
    async def test_result_includes_movie_metadata(self, mock_tmdb):
        result = await validate_move(
            mock_tmdb, "Chris Hemsworth", "Thor", "Natalie Portman"
        )
        assert result.movie_id == 10195
        assert result.movie_title == "Thor"
        assert result.movie_year == "2011"
        assert result.poster_url is not None
