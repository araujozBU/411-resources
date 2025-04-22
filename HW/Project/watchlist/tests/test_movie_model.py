import pytest

from watchlist.models.movie_model import Movies

# --- Fixtures ---

@pytest.fixture
def movie_beatles(session):
    """Fixture for The Beatles - Hey Jude."""
    movie = Movies(director="The Beatles", title="Hey Jude", year=1968, genre="Rock", duration=431)
    session.add(movie)
    session.commit()
    return movie

@pytest.fixture
def movie_nirvana(session):
    """Fixture for Nirvana - Smells Like Teen Spirit."""
    movie = Movies(director="Nirvana", title="Smells Like Teen Spirit", year=1991, genre="Grunge", duration=301)
    session.add(movie)
    session.commit()
    return movie

# --- Create Movie ---

def test_create_movie(session):
    """Test creating a new movie."""
    Movies.create_movie("Queen", "Bohemian Rhapsody", 1975, "Rock", 354)
    movie = session.query(Movies).filter_by(title="Bohemian Rhapsody").first()
    assert movie is not None
    assert movie.director == "Queen"


def test_create_duplicate_movie(session, movie_beatles):
    """Test creating a movie with a duplicate director/title/year."""
    with pytest.raises(ValueError, match="already exists"):
        Movies.create_movie("The Beatles", "Hey Jude", 1968, "Rock", 431)


@pytest.mark.parametrize("director, title, year, genre, duration", [
    ("", "Valid Title", 2000, "Pop", 180),
    ("Valid Director", "", 2000, "Pop", 180),
    ("Valid Director", "Valid Title", 1899, "Pop", 180),
    ("Valid Director", "Valid Title", 2000, "", 180),
    ("Valid Director", "Valid Title", 2000, "Pop", 0),
])
def test_create_movie_invalid_data(director, title, year, genre, duration):
    """Test validation errors when creating a movie."""
    with pytest.raises(ValueError):
        Movies.create_movie(director, title, year, genre, duration)

# --- Get Movie ---

def test_get_movie_by_id(movie_beatles):
    """Test fetching a movie by ID."""
    fetched = Movies.get_movie_by_id(movie_beatles.id)
    assert fetched.title == "Hey Jude"


def test_get_movie_by_id_not_found(app):
    """Test error when fetching nonexistent movie by ID."""
    with pytest.raises(ValueError, match="not found"):
        Movies.get_movie_by_id(999)


def test_get_movie_by_compound_key(movie_nirvana):
    """Test fetching a movie by compound key."""
    movie = Movies.get_movie_by_compound_key("Nirvana", "Smells Like Teen Spirit", 1991)
    assert movie.genre == "Grunge"


def test_get_movie_by_compound_key_not_found(app):
    """Test error when fetching nonexistent movie by compound key."""
    with pytest.raises(ValueError, match="not found"):
        Movies.get_movie_by_compound_key("Ghost", "Invisible Movie", 2024)

# --- Delete Movie ---

def test_delete_movie_by_id(session, movie_beatles):
    """Test deleting a movie by ID."""
    Movies.delete_movie(movie_beatles.id)
    assert session.get(Movies, movie_beatles.id) is None


def test_delete_movie_not_found(app):
    """Test deleting a non-existent movie by ID."""
    with pytest.raises(ValueError, match="not found"):
        Movies.delete_movie(999)

# --- Play Count ---

def test_update_play_count(session, movie_nirvana):
    """Test incrementing play count."""
    assert movie_nirvana.play_count == 0
    movie_nirvana.update_play_count()
    session.refresh(movie_nirvana)
    assert movie_nirvana.play_count == 1

# --- Get All Movies ---

def test_get_all_movies(session, movie_beatles, movie_nirvana):
    """Test retrieving all movies."""
    movies = Movies.get_all_movies()
    assert len(movies) == 2


def test_get_all_movies_sorted(session, movie_beatles, movie_nirvana):
    """Test retrieving movies sorted by play count."""
    movie_nirvana.play_count = 5
    movie_beatles.play_count = 3
    session.commit()
    sorted_movies = Movies.get_all_movies(sort_by_play_count=True)
    assert sorted_movies[0]["title"] == "Smells Like Teen Spirit"

# --- Random Movie ---

def test_get_random_movie(session, movie_beatles, movie_nirvana):
    """Test getting a random movie as a dictionary with expected fields."""
    movie = Movies.get_random_movie()
    assert isinstance(movie, dict)
    expected_keys = {"id", "director", "title", "year", "genre", "duration", "play_count"}
    assert set(movie.keys()) == expected_keys


def test_get_random_movie_empty(session):
    """Test error when no movies exist."""
    Movies.query.delete()
    session.commit()
    with pytest.raises(ValueError, match="empty"): 
        Movies.get_random_movie()
