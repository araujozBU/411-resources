import pytest

from watchlist.models.watchlist_model import WatchlistModel
from watchlist.models.movie_model import Movies

@pytest.fixture()
def watchlist_model():
    """Fixture to provide a new instance of WatchlistModel for each test."""
    return WatchlistModel()

# Fixtures providing sample movies for the tests.
@pytest.fixture
def movie_beatles(session):
    """Fixture for a Beatles movie entry."""
    movie = Movies(
        director="The Beatles",
        title="Come Together",
        year=1969,
        genre="Rock",
        duration=259
    )
    session.add(movie)
    session.commit()
    return movie

@pytest.fixture
def movie_nirvana(session):
    """Fixture for a Nirvana movie entry."""
    movie = Movies(
        director="Nirvana",
        title="Smells Like Teen Spirit",
        year=1991,
        genre="Grunge",
        duration=301
    )
    session.add(movie)
    session.commit()
    return movie

@pytest.fixture
def sample_watchlist(movie_beatles, movie_nirvana):
    """Fixture for a sample watchlist content."""
    return [movie_beatles, movie_nirvana]

# Add / Remove Movie Management Test Cases

def test_add_movie_to_watchlist(watchlist_model, movie_beatles, mocker):
    """Test adding a movie to the watchlist."""
    mocker.patch(
        "watchlist.models.watchlist_model.Movies.get_movie_by_id",
        return_value=movie_beatles
    )
    watchlist_model.add_movie_to_watchlist(movie_beatles.id)
    assert len(watchlist_model.watchlist) == 1
    assert watchlist_model.watchlist[0] == movie_beatles.id


def test_add_duplicate_movie_to_watchlist(watchlist_model, movie_beatles, mocker):
    """Test error when adding a duplicate movie to the watchlist."""
    mocker.patch(
        "watchlist.models.watchlist_model.Movies.get_movie_by_id",
        side_effect=[movie_beatles, movie_beatles]
    )
    watchlist_model.add_movie_to_watchlist(movie_beatles.id)
    with pytest.raises(ValueError, match="already in watchlist"):
        watchlist_model.add_movie_to_watchlist(movie_beatles.id)


def test_remove_movie_by_id(watchlist_model, movie_beatles, mocker):
    """Test removing a movie from the watchlist by ID."""
    mocker.patch(
        "watchlist.models.watchlist_model.Movies.get_movie_by_id",
        return_value=movie_beatles
    )
    watchlist_model.watchlist = [1, 2]
    watchlist_model.remove_movie_by_id(1)
    assert len(watchlist_model.watchlist) == 1
    assert watchlist_model.watchlist[0] == 2


def test_remove_movie_by_position(watchlist_model):
    """Test removing a movie from the watchlist by position."""
    watchlist_model.watchlist = [1, 2]
    watchlist_model.remove_movie_by_position(1)
    assert watchlist_model.watchlist == [2]


def test_clear_watchlist(watchlist_model):
    """Test clearing the entire watchlist."""
    watchlist_model.watchlist.append(1)
    watchlist_model.clear_watchlist()
    assert watchlist_model.watchlist == []

# Watchlist Retrieval Test Cases

def test_get_all_movies(watchlist_model, sample_watchlist, mocker):
    """Test retrieving all movies from the watchlist."""
    mocker.patch(
        "watchlist.models.watchlist_model.WatchlistModel._get_movie_from_cache_or_db",
        side_effect=sample_watchlist
    )
    watchlist_model.watchlist = [1, 2]
    all_movies = watchlist_model.get_all_movies()
    assert len(all_movies) == 2
    assert all_movies[0].id == 1


def test_get_movie_by_id(watchlist_model, movie_beatles, mocker):
    """Test retrieving a movie by ID from the watchlist."""
    mocker.patch(
        "watchlist.models.watchlist_model.Movies.get_movie_by_id",
        return_value=movie_beatles
    )
    watchlist_model.watchlist = [1]
    m = watchlist_model.get_movie_by_id(1)
    assert m.id == 1
    assert m.title == 'Come Together'


def test_get_movie_by_position(watchlist_model, movie_beatles, mocker):
    """Test retrieving a movie by position in the watchlist."""
    mocker.patch(
        "watchlist.models.watchlist_model.WatchlistModel._get_movie_from_cache_or_db",
        return_value=movie_beatles
    )
    watchlist_model.watchlist = [1]
    m = watchlist_model.get_movie_by_position(1)
    assert m.id == 1


def test_get_current_movie(watchlist_model, movie_beatles, mocker):
    """Test retrieving the current movie in the watchlist."""
    mocker.patch(
        "watchlist.models.watchlist_model.WatchlistModel._get_movie_from_cache_or_db",
        return_value=movie_beatles
    )
    watchlist_model.watchlist = [1]
    cm = watchlist_model.get_current_movie()
    assert cm.id == 1


def test_get_watchlist_length_and_duration(watchlist_model, sample_watchlist, mocker):
    """Test retrieving length and total duration of the watchlist."""
    mocker.patch(
        "watchlist.models.watchlist_model.WatchlistModel._get_movie_from_cache_or_db",
        side_effect=sample_watchlist
    )
    watchlist_model.watchlist = [1, 2]
    assert watchlist_model.get_watchlist_length() == 2
    assert watchlist_model.get_watchlist_duration() == sample_watchlist[0].duration + sample_watchlist[1].duration

# Utility Function Test Cases

def test_validate_movie_id_and_position(watchlist_model, sample_watchlist, mocker):
    """Test validation helpers for movie ID and position."""
    mocker.patch(
        "watchlist.models.watchlist_model.WatchlistModel._get_movie_from_cache_or_db",
        side_effect=sample_watchlist
    )
    watchlist_model.watchlist = [1]
    # validate movie ID
    assert watchlist_model.validate_movie_id(1) == 1
    # validate position
    assert watchlist_model.validate_position(1) == 1


def test_check_if_empty_raises(watchlist_model):
    """Test that check_if_empty raises on empty watchlist."""
    with pytest.raises(ValueError):
        watchlist_model.check_if_empty()
