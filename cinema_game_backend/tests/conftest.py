import pytest


@pytest.fixture
def departed_cast():
    return [
        "Leonardo DiCaprio",
        "Matt Damon",
        "Jack Nicholson",
        "Mark Wahlberg",
        "Martin Sheen",
        "Ray Winstone",
        "Vera Farmiga",
        "Alec Baldwin",
    ]


@pytest.fixture
def apocalypse_now_cast():
    return [
        "Marlon Brando",
        "Martin Sheen",
        "Robert Duvall",
        "Frederic Forrest",
        "Sam Bottoms",
        "Laurence Fishburne",
        "Dennis Hopper",
    ]


@pytest.fixture
def toy_story_cast():
    return [
        "Tom Hanks",
        "Tim Allen",
        "Don Rickles",
        "Jim Varney",
        "Wallace Shawn",
        "John Ratzenberger",
        "Annie Potts",
    ]
