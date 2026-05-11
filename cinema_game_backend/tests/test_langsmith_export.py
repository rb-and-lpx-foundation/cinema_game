"""Tests for LangSmith export utilities using mocked Client responses."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

from cinema_game_backend.experiments.langsmith_export import (
    list_game_ids,
    export_game,
)
from cinema_game_backend.models.experiment import ExpectedSuccess, ExpectedFailure


def _mock_run(name, metadata=None, inputs=None, outputs=None, start_time=None):
    run = MagicMock()
    run.name = name
    run.metadata = metadata or {}
    run.inputs = inputs or {}
    run.outputs = outputs or {}
    run.start_time = start_time or datetime(2026, 5, 10, 12, 0, 0)
    run.id = f"run-{id(run)}"
    return run


@pytest.fixture
def new_game_run():
    return _mock_run(
        name="new_game",
        metadata={"game_id": "abc-123", "difficulty": "medium"},
        outputs={
            "start_actor": {"name": "Brad Pitt", "id": 287},
            "end_actor": {"name": "Colin Firth", "id": 1891},
            "difficulty": "medium",
            "min_moves": 3,
        },
    )


@pytest.fixture
def valid_move_run():
    return _mock_run(
        name="make_move",
        metadata={"game_id": "abc-123"},
        inputs={
            "body": {"movie": "12 Years a Slave", "next_actor": "Michael Fassbender"}
        },
        outputs={
            "valid": True,
            "movie_id": 76203,
            "movie_title": "12 Years a Slave",
            "current_actor": {"name": "Michael Fassbender", "id": 17288},
        },
        start_time=datetime(2026, 5, 10, 12, 1, 0),
    )


@pytest.fixture
def invalid_move_run():
    return _mock_run(
        name="make_move",
        metadata={"game_id": "abc-123"},
        inputs={"body": {"movie": "Batman", "next_actor": "Jack Nicholson"}},
        outputs={"valid": False},
        start_time=datetime(2026, 5, 10, 12, 2, 0),
    )


@pytest.fixture
def mock_client(new_game_run, valid_move_run, invalid_move_run):
    client = MagicMock()

    # list_runs returns different results depending on the filter.
    def list_runs_side_effect(**kwargs):
        filt = kwargs.get("filter", "")
        if "new_game" in filt:
            return iter([new_game_run])
        else:
            return iter([new_game_run, valid_move_run, invalid_move_run])

    client.list_runs.side_effect = list_runs_side_effect
    return client


class TestListGameIds:
    def test_returns_game_metadata(self, mock_client, new_game_run):
        mock_client.list_runs.side_effect = None
        mock_client.list_runs.return_value = iter([new_game_run])

        games = list_game_ids(client=mock_client, limit=5)

        assert len(games) == 1
        assert games[0]["game_id"] == "abc-123"
        assert games[0]["difficulty"] == "medium"
        assert games[0]["start_actor"] == "Brad Pitt"
        assert games[0]["end_actor"] == "Colin Firth"

    def test_empty_when_no_runs(self, mock_client):
        mock_client.list_runs.side_effect = None
        mock_client.list_runs.return_value = iter([])

        games = list_game_ids(client=mock_client)
        assert games == []


class TestExportGame:
    def test_exports_valid_and_invalid_moves(self, mock_client):
        game = export_game("abc-123", client=mock_client)

        assert game.start_actor == "Brad Pitt"
        assert game.end_actor == "Colin Firth"
        assert len(game.moves) == 2

    def test_valid_move_has_expected_success(self, mock_client):
        game = export_game("abc-123", client=mock_client)

        valid_move = game.moves[0]
        assert valid_move.movie == "12 Years a Slave"
        assert valid_move.actor == "Michael Fassbender"
        assert isinstance(valid_move.expected, ExpectedSuccess)
        assert valid_move.expected.movie_id == 76203
        assert valid_move.expected.actor_name == "Michael Fassbender"
        assert valid_move.expected.actor_id == 17288

    def test_invalid_move_has_expected_failure(self, mock_client):
        game = export_game("abc-123", client=mock_client)

        invalid_move = game.moves[1]
        assert invalid_move.movie == "Batman"
        assert invalid_move.actor == "Jack Nicholson"
        assert isinstance(invalid_move.expected, ExpectedFailure)

    def test_moves_ordered_by_time(self, mock_client):
        game = export_game("abc-123", client=mock_client)

        # First move is the valid one (12:01), second is invalid (12:02).
        assert game.moves[0].movie == "12 Years a Slave"
        assert game.moves[1].movie == "Batman"

    def test_raises_when_no_new_game_trace(self, mock_client):
        mock_client.list_runs.side_effect = None
        mock_client.list_runs.return_value = iter([])

        with pytest.raises(ValueError, match="No new_game trace found"):
            export_game("nonexistent", client=mock_client)

    def test_game_with_no_moves(self, mock_client, new_game_run):
        mock_client.list_runs.side_effect = None
        mock_client.list_runs.return_value = iter([new_game_run])

        game = export_game("abc-123", client=mock_client)

        assert game.start_actor == "Brad Pitt"
        assert game.end_actor == "Colin Firth"
        assert game.moves == []

    def test_round_trip_serialization(self, mock_client):
        game = export_game("abc-123", client=mock_client)

        json_str = game.model_dump_json()
        restored = game.model_validate_json(json_str)
        assert restored == game
