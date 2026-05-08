"""
Validation Agent: verifies that two actors both appeared in a named movie.

Uses direct TMDb lookups and fuzzy string matching — no LLM calls required.
TMDb handles fuzzy movie title search server-side. Actor name matching against
the cast list uses rapidfuzz (see matching.py).
"""

import logging
from langsmith import traceable
from art_graph.cinema_data_providers.tmdb.client import TMDbClient
from ..matching import find_actor_in_cast
from ..models.game import Confidence, ValidationResult

logger = logging.getLogger(__name__)


@traceable(run_type="chain", name="validate_move")
async def validate_move(
    tmdb: TMDbClient, from_actor: str, movie_title: str, to_actor: str
) -> ValidationResult:
    """
    Verify that from_actor and to_actor both appeared in movie_title.

    1. Search TMDb for the movie (TMDb handles fuzzy title matching).
    2. Fetch the cast list.
    3. Fuzzy-match both actor names against the cast.
    """
    movie = await tmdb.search_movie(movie_title)
    if not movie:
        return ValidationResult(
            valid=False,
            explanation=f"Movie '{movie_title}' not found on TMDb.",
            confidence=Confidence.high,
        )

    cast = await tmdb.get_movie_cast(movie.id)
    cast_names = [c.name for c in cast]

    from_match = find_actor_in_cast(from_actor, cast_names)
    to_match = find_actor_in_cast(to_actor, cast_names)

    valid = from_match is not None and to_match is not None

    if valid:
        explanation = (
            f"{from_match.matched_name} and {to_match.matched_name} "
            f"both appear in {movie.title} ({movie.year})."
        )
    else:
        missing = []
        if from_match is None:
            missing.append(from_actor)
        if to_match is None:
            missing.append(to_actor)
        explanation = (
            f"{' and '.join(missing)} not found in the cast of "
            f"{movie.title} ({movie.year})."
        )

    return ValidationResult(
        valid=valid,
        explanation=explanation,
        confidence=Confidence.high,
        movie_id=movie.id,
        movie_title=movie.title,
        movie_year=movie.year,
        poster_url=movie.poster_url,
        backdrop_url=movie.backdrop_url,
        from_actor_found=from_match is not None,
        to_actor_found=to_match is not None,
        from_actor_name=from_match.matched_name if from_match else None,
        to_actor_name=to_match.matched_name if to_match else None,
    )
