"""Export game sessions from the database into RecordedGame models."""

from ..database import load_game
from ..models.experiment import (
    ExpectedSuccess,
    RecordedMove,
    RecordedGame,
)


def export_game(game_id: str) -> RecordedGame:
    """Load a game from the database and return it as a RecordedGame.

    Only valid (accepted) moves are stored in the database, so every
    move in the returned RecordedGame has an ExpectedSuccess outcome.
    """
    game = load_game(game_id)
    if game is None:
        raise ValueError(f"Game not found: {game_id}")

    moves = []
    for m in game["moves"]:
        expected = ExpectedSuccess(
            movie_id=m["movie_id"],
            movie_title=m["movie_title"],
            actor_name=m["to_actor"],
        )
        moves.append(
            RecordedMove(movie=m["movie"], actor=m["to_actor"], expected=expected)
        )

    return RecordedGame(
        start_actor=game["start_actor"]["name"],
        end_actor=game["end_actor"]["name"],
        moves=moves,
    )
