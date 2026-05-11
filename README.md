# Cinema Game

Connect two actors through shared movies — one hop at a time.

Brad Pitt and Michael Fassbender were both in *12 Years a Slave*. Michael Fassbender and Nicholas Hoult were both in *X-Men: Apocalypse*. Nicholas Hoult and Colin Firth were both in *A Single Man*. That's a path of length 3 connecting Brad Pitt to Colin Firth.

Can you find it faster?

## How it works

The backend generates a puzzle: a start actor, an end actor, and a guaranteed solution path. You play by naming a movie the current actor appeared in, then naming a co-star from that movie. Each move is verified in real time using TMDb data and fuzzy string matching — typos and minor misspellings are handled gracefully. An optional LLM fallback resolves harder cases like nicknames ("Larry" for "Laurence").

**Difficulty levels:**
| Level | Hops | Notes |
|-------|------|-------|
| Easy | 2 | No movie repeated |
| Medium | 3–5 | Random within range |
| Hard | 6–8 | — |

## Stack

| Layer      | Technology                                                                                           |
|------------|------------------------------------------------------------------------------------------------------|
| Backend    | FastAPI (Python)                                                                                     |
| Matching   | [rapidfuzz](https://github.com/rapidfuzz/RapidFuzz) (Levenshtein + WRatio)                          |
| LLM fallback | Optional, via [reusable-llm-provider](https://github.com/newexo/reusable-llm-provider) (nickname resolution) |
| Movie data | TMDb API via [art-graph](https://github.com/ChiPowers/artist-graph)                                 |
| TMDb cache | SQLAlchemy (SQLite locally, Postgres/MySQL in production)                                            |
| Database   | SQLite (game state)                                                                                  |
| Tracing    | LangSmith (optional)                                                                                 |
| Frontend   | Next.js, Tailwind CSS, Framer Motion ([separate repo](https://github.com/ChiPowers/cinema-frontend)) |

## Getting started

### Backend

Requires Python >=3.10, <3.15.

```bash
poetry install
```

To also install dev tools (ruff, pytest):

```bash
poetry install --with dev
```

To install notebook and visualization dependencies (jupyter, matplotlib, seaborn):

```bash
poetry install --with notebook
```

Or install everything:

```bash
poetry install --with dev,notebook
```

### Configuration

Copy `secrets/.env.example` to `secrets/.env` and fill in your keys:

```
TMDB_API_KEY=...          # Required
ANTHROPIC_API_KEY=...     # Optional — enables LLM fallback for nickname resolution
```

**TMDb cache** — one of these must be set or the app will refuse to start:

| Variable | Effect |
|----------|--------|
| `TMDB_CACHE_PATH=/path/to/tmdb_cache.db` | Enable SQLite-backed TMDb caching at the given path |
| `TMDB_CACHE_DISABLE=true` | Run without caching (every request hits TMDb directly) |

For local development, `TMDB_CACHE_DISABLE=true` is the simplest option. For production or heavy use, set `TMDB_CACHE_PATH` to a writable file path — this dramatically reduces TMDb API calls.

**LangSmith tracing** (optional):

```
LANGSMITH_TRACING_V2=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=cinema-game
```

See `secrets/README.md` for more detail.

### LangSmith trace structure

Each player move produces a `validate_move` trace with the following child spans:

```
validate_move (chain)
├── resolve_actor (tool)   — from_actor
│   └── llm_name_match (tool)   — only if fuzzy matching failed and LLM is available
└── resolve_actor (tool)   — to_actor
    └── llm_name_match (tool)   — only if fuzzy matching failed and LLM is available
```

**Reading the traces:**

| What you see | What it means |
|---|---|
| `resolve_actor` returns an `ActorMatch` with no `llm_name_match` child | Fuzzy matching succeeded |
| `resolve_actor` has an `llm_name_match` child that returns an `ActorMatch` | Fuzzy matching failed, LLM resolved the name (e.g. nickname) |
| `resolve_actor` has an `llm_name_match` child that returns `None` | Both fuzzy matching and LLM failed |
| `resolve_actor` returns `None` with no `llm_name_match` child | Fuzzy matching failed and no LLM provider is configured |

When the LLM fallback is skipped, the `resolve_actor` span carries explicit metadata:
- `llm_fallback_skipped: true`
- `unresolved_query: "<player input>"`

These metadata fields are filterable in the LangSmith UI, making it easy to find moves where an LLM provider would have helped.

### LLM experiment harness (LangSmith)

Run a model matrix over Cinema Game prompt surfaces and log each model run as a LangSmith experiment:

```bash
poetry run python scripts/run_llm_experiments.py --prefix cinema-game-llm-matrix
```

Run only a subset:

```bash
poetry run python scripts/run_llm_experiments.py --models haiku_4_5,sonnet_4_5,gpt_5_mini
```

Current model aliases:
- `haiku_4_5`
- `sonnet_4_5`
- `gpt_5_mini`
- `kimi_k2`
- `gemini_3_flash`
- `llama_4_maverick`

If a provider's canonical model id changes, set the `EXPERIMENT_MODEL_*` env vars in `secrets/.env`.

### Development with Make

A `Makefile` provides standard development commands:

| Target                | Description                                         |
|-----------------------|-----------------------------------------------------|
| `make test`           | Run unit tests                                      |
| `make test-functional`| Run functional tests (requires API credentials)     |
| `make test-all`       | Run unit + functional tests                         |
| `make lint`           | Lint with ruff                                      |
| `make format`         | Format with ruff                                    |
| `make check`          | Format + lint + test                                |
| `make coverage`       | Run unit tests with coverage enforcement (50% min)  |
| `make coverage-html`  | Generate an HTML coverage report at `htmlcov/`      |

### Running the server

```bash
poetry run uvicorn cinema_game_backend.main:app --reload
```

API runs at `http://localhost:8000`.

### Frontend

See the [frontend repo](https://github.com/ChiPowers/cinema-frontend).

## API

| Method   | Route                                     | Description                           |
|----------|-------------------------------------------|---------------------------------------|
| `POST`   | `/game/new?difficulty=easy\|medium\|hard` | Generate a new puzzle                 |
| `POST`   | `/game/{id}/move`                         | Submit a move `{ movie, next_actor }` |
| `DELETE`  | `/game/{id}/move`                         | Undo the last move                    |
| `GET`    | `/game/{id}`                              | Get current game state                |
| `GET`    | `/health`                                 | Health check                          |

## Game session replay

The `experiments` package provides tools for recording and replaying game sessions for regression testing and analysis.

### Recorded game format

A recorded game is a JSON file containing a start actor, end actor, and a list of moves with expected outcomes:

```json
{
  "start_actor": "Brad Pitt",
  "end_actor": "Colin Firth",
  "moves": [
    {
      "movie": "12 Years a Slave",
      "actor": "Michael Fassbender",
      "expected": {
        "valid": true,
        "movie_id": 76203,
        "movie_title": "12 Years a Slave",
        "actor_id": 17288,
        "actor_name": "Michael Fassbender"
      }
    },
    {
      "movie": "Batman",
      "actor": "Jack Nicholson",
      "expected": { "valid": false }
    }
  ]
}
```

### Exporting from LangSmith

Games played with LangSmith tracing enabled can be exported into this format:

```python
from cinema_game_backend.experiments.langsmith_export import list_game_ids, export_game

for g in list_game_ids():
    print(g["game_id"], g["start_actor"], "->", g["end_actor"])

game = export_game("some-game-id")
Path("game.json").write_text(game.model_dump_json(indent=2))
```

### Replaying against live TMDb

Replay a recorded game through `validate_move` and compare actual vs expected outcomes:

```python
from cinema_game_backend.config import create_tmdb_client
from cinema_game_backend.experiments.replay import replay_game
from cinema_game_backend.models.experiment import RecordedGame

game = RecordedGame.model_validate_json(Path("game.json").read_text())
results = await replay_game(create_tmdb_client(), game)

for r in results:
    status = "PASS" if r.passed else "FAIL"
    print(f"[{status}] [{r.move.movie}] {r.move.actor}: {r.detail}")
```

### Notebook

The `notebooks/replay_game_session.ipynb` notebook provides an interactive workflow for exporting, inspecting, and replaying game sessions. Install notebook dependencies first:

```bash
poetry install --with notebook
```

## Architecture

The backend uses **FastAPI dependency injection** to provide the TMDb client and an optional LLM provider. At startup, `create_tmdb_client()` reads the cache configuration and produces either a `CachedTMDbClient` (backed by SQLAlchemy) or a plain `TMDbClient`. If an LLM API key is configured, `create_llm_provider()` creates a provider via reusable-llm-provider. Both are stored on `app.state` and injected into route handlers via `Depends()`.

**Move validation** works in three stages:
1. **TMDb lookup** — search for the movie and fetch its cast list.
2. **Fuzzy matching** — rapidfuzz Levenshtein distance + WRatio scoring resolves typos and minor misspellings against the cast list.
3. **LLM fallback** (optional) — if fuzzy matching fails and an LLM provider is available, an LLM call resolves harder cases like nicknames ("Larry" → "Laurence").

The TMDb cache layer lives in the [art-graph](https://github.com/ChiPowers/artist-graph) library. It caches people, movies, and credits in three tables. The caller (this app) owns the database engine and configuration — art-graph has no opinion about which database backend is used.

## Attribution

Movie and actor data provided by [TMDb](https://www.themoviedb.org). This product uses the TMDb API but is not endorsed or certified by TMDb.
