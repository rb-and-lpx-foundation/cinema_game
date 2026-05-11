"""Export game sessions from LangSmith traces into RecordedGame models."""

from langsmith import Client
from langsmith.utils import get_tracer_project
from ..models.experiment import (
    ExpectedSuccess,
    ExpectedFailure,
    RecordedMove,
    RecordedGame,
)


def _get_client() -> Client:
    """Create a LangSmith client. Requires LANGSMITH_API_KEY in the environment."""
    return Client()


def list_game_ids(client: Client | None = None, limit: int = 10) -> list[dict]:
    """List recent game sessions with their metadata.

    Returns a list of dicts with keys: game_id, difficulty, start_actor,
    end_actor, start_time.
    """
    client = client or _get_client()
    runs = client.list_runs(
        project_name=get_tracer_project(),
        filter='eq(name, "new_game")',
        limit=limit,
    )

    games = []
    for run in runs:
        metadata = run.metadata or {}
        outputs = run.outputs or {}
        games.append(
            {
                "game_id": metadata.get("game_id"),
                "difficulty": metadata.get("difficulty"),
                "start_actor": outputs.get("start_actor", {}).get("name"),
                "end_actor": outputs.get("end_actor", {}).get("name"),
                "start_time": run.start_time,
            }
        )
    return games


def export_game(game_id: str, client: Client | None = None) -> RecordedGame:
    """Export a game session from LangSmith into a RecordedGame.

    Fetches the new_game and make_move traces for the given game_id,
    extracts player inputs and validation outcomes, and returns a
    RecordedGame ready for replay or serialization.
    """
    client = client or _get_client()
    project = get_tracer_project()

    # Fetch all runs for this game.
    runs = list(
        client.list_runs(
            project_name=project,
            filter=f'has(metadata, "game_id") and eq(metadata.game_id, "{game_id}")',
        )
    )

    # Extract puzzle setup from new_game run.
    new_game_run = next((r for r in runs if r.name == "new_game"), None)
    if not new_game_run or not new_game_run.outputs:
        raise ValueError(f"No new_game trace found for game_id={game_id}")

    start_actor = new_game_run.outputs["start_actor"]["name"]
    end_actor = new_game_run.outputs["end_actor"]["name"]

    # Extract moves from make_move runs, ordered by time.
    move_runs = sorted(
        [r for r in runs if r.name == "make_move"],
        key=lambda r: r.start_time,
    )

    moves = []
    for run in move_runs:
        inputs = run.inputs or {}
        outputs = run.outputs or {}

        # The raw player input is in the request body.
        movie = inputs.get("body", {}).get("movie", "")
        actor = inputs.get("body", {}).get("next_actor", "")

        valid = outputs.get("valid", False)

        if valid:
            expected = ExpectedSuccess(
                movie_id=outputs.get("movie_id", 0),
                movie_title=outputs.get("movie_title", ""),
                actor_id=outputs.get("current_actor", {}).get("id", 0),
                actor_name=outputs.get("current_actor", {}).get("name", ""),
            )
        else:
            expected = ExpectedFailure()

        moves.append(RecordedMove(movie=movie, actor=actor, expected=expected))

    return RecordedGame(start_actor=start_actor, end_actor=end_actor, moves=moves)
