import logging
import os
import time
from typing import List

from watchlist.models.movie_model import Movies
from watchlist.utils.api_utils import get_random
from watchlist.utils.logger import configure_logger

logger = logging.getLogger(__name__)
configure_logger(logger)


class WatchlistModel:
    """
    A class to manage an in-memory watchlist of movies.
    """

    def __init__(self):
        """
        Initializes the WatchlistModel with an empty watchlist and current position set to 1.

        The watchlist is a list of Movie IDs, and current position is 1-indexed.
        TTL (Time To Live) for movie caching is set via env var "TTL" (default 60 sec).
        """
        self.current_position = 1
        self.watchlist: List[int] = []
        self._movie_cache: dict[int, Movies] = {}
        self._ttl: dict[int, float] = {}
        self.ttl_seconds = int(os.getenv("TTL", 60))

    def _get_movie_from_cache_or_db(self, movie_id: int) -> Movies:
        """
        Retrieves a movie by ID from cache (if valid) or DB.
        """
        now = time.time()
        if movie_id in self._movie_cache and self._ttl.get(movie_id, 0) > now:
            logger.debug(f"Movie ID {movie_id} retrieved from cache")
            return self._movie_cache[movie_id]

        try:
            movie = Movies.get_movie_by_id(movie_id)
            logger.info(f"Movie ID {movie_id} loaded from DB")
        except ValueError as e:
            logger.error(f"Movie ID {movie_id} not found in DB: {e}")
            raise ValueError(f"Movie ID {movie_id} not found in database") from e

        self._movie_cache[movie_id] = movie
        self._ttl[movie_id] = now + self.ttl_seconds
        return movie

    def add_movie_to_watchlist(self, movie_id: int) -> None:
        """
        Adds a movie to the watchlist by ID.
        """
        logger.info(f"Received request to add movie ID {movie_id} to watchlist")
        movie_id = self.validate_movie_id(movie_id, check_in_watchlist=False)
        if movie_id in self.watchlist:
            logger.error(f"Movie ID {movie_id} already in watchlist")
            raise ValueError(f"Movie ID {movie_id} already in watchlist")

        try:
            movie = self._get_movie_from_cache_or_db(movie_id)
        except ValueError as e:
            logger.error(f"Failed to add movie: {e}")
            raise

        self.watchlist.append(movie.id)
        logger.info(f"Added to watchlist: {movie.director} - {movie.title} ({movie.year})")

    def remove_movie_by_id(self, movie_id: int) -> None:
        """
        Removes a movie from the watchlist by its ID.
        """
        logger.info(f"Received request to remove movie ID {movie_id} from watchlist")
        self.check_if_empty()
        movie_id = self.validate_movie_id(movie_id)

        if movie_id not in self.watchlist:
            logger.warning(f"Movie ID {movie_id} not in watchlist")
            raise ValueError(f"Movie ID {movie_id} not in watchlist")

        self.watchlist.remove(movie_id)
        logger.info(f"Removed movie ID {movie_id} from watchlist")

    def remove_movie_by_position(self, position: int) -> None:
        """
        Removes a movie from the watchlist by its position (1-indexed).
        """
        logger.info(f"Removing movie at position {position}")
        self.check_if_empty()
        pos = self.validate_position(position)
        del self.watchlist[pos - 1]
        logger.info(f"Movie removed at position {position}")

    def clear_watchlist(self) -> None:
        """
        Clears all movies from the watchlist.
        """
        logger.info("Clearing watchlist")
        try:
            self.check_if_empty()
        except ValueError:
            logger.warning("Watchlist already empty")
        self.watchlist.clear()
        logger.info("Watchlist cleared")

    def get_all_movies(self) -> List[Movies]:
        """
        Returns list of all movies in watchlist.
        """
        self.check_if_empty()
        logger.info("Retrieving all movies in watchlist")
        return [self._get_movie_from_cache_or_db(m_id) for m_id in self.watchlist]

    def get_movie_by_id(self, movie_id: int) -> Movies:
        """
        Retrieves a movie by its ID.
        """
        self.check_if_empty()
        m_id = self.validate_movie_id(movie_id)
        movie = self._get_movie_from_cache_or_db(m_id)
        logger.info(f"Retrieved movie: {movie.director} - {movie.title} ({movie.year})")
        return movie

    def get_movie_by_position(self, position: int) -> Movies:
        """
        Retrieves a movie by its position in the watchlist.
        """
        self.check_if_empty()
        pos = self.validate_position(position)
        movie_id = self.watchlist[pos - 1]
        movie = self._get_movie_from_cache_or_db(movie_id)
        logger.info(f"Retrieved movie: {movie.director} - {movie.title} ({movie.year})")
        return movie

    def get_current_movie(self) -> Movies:
        """
        Returns the current movie in the watchlist.
        """
        return self.get_movie_by_position(self.current_position)

    def get_watchlist_length(self) -> int:
        """
        Returns number of movies in watchlist.
        """
        length = len(self.watchlist)
        logger.info(f"Watchlist length: {length}")
        return length

    def get_watchlist_duration(self) -> int:
        """
        Returns total duration of all movies in watchlist.
        """
        total = sum(self._get_movie_from_cache_or_db(m_id).duration for m_id in self.watchlist)
        logger.info(f"Total watchlist duration: {total}")
        return total

    def go_to_position(self, position: int) -> None:
        """
        Sets current position to specified index.
        """
        self.check_if_empty()
        pos = self.validate_position(position)
        self.current_position = pos
        logger.info(f"Current position set to {pos}")

    def go_to_random_position(self) -> None:
        """
        Sets current position to a random movie.
        """
        self.check_if_empty()
        rand = get_random(len(self.watchlist))
        self.current_position = rand
        logger.info(f"Random position set to {rand}")

    def swap_movies(self, pos1: int, pos2: int) -> None:
        """
        Swaps two movies by their positions.
        """
        self.check_if_empty()
        p1, p2 = self.validate_position(pos1), self.validate_position(pos2)
        if p1 == p2:
            logger.error(f"Cannot swap same positions: {p1}")
            raise ValueError("Cannot swap the same movie")
        self.watchlist[p1-1], self.watchlist[p2-1] = self.watchlist[p2-1], self.watchlist[p1-1]
        logger.info(f"Swapped movies at positions {p1} and {p2}")

    def validate_movie_id(self, movie_id: int, check_in_watchlist: bool = True) -> int:
        """
        Validates the movie ID.
        """
        try:
            mid = int(movie_id)
            if mid < 0:
                raise ValueError
        except:
            logger.error(f"Invalid movie id: {movie_id}")
            raise ValueError(f"Invalid movie id: {movie_id}")
        if check_in_watchlist and mid not in self.watchlist:
            logger.error(f"Movie id {mid} not in watchlist")
            raise ValueError(f"Movie id {mid} not in watchlist")
        try:
            self._get_movie_from_cache_or_db(mid)
        except Exception as e:
            logger.error(f"Movie id {mid} not found in database: {e}")
            raise ValueError(f"Movie id {mid} not found in database")
        return mid

    def validate_position(self, position: int) -> int:
        """
        Validates a 1-indexed position within the watchlist.
        """
        try:
            pos = int(position)
            if not (1 <= pos <= len(self.watchlist)):
                raise ValueError
            return pos
        except:
            logger.error(f"Invalid position: {position}")
            raise ValueError(f"Invalid position: {position}")

    def check_if_empty(self) -> None:
        """
        Raises ValueError if the watchlist is empty.
        """
        if not self.watchlist:
            logger.error("Watchlist is empty")
            raise ValueError("Watchlist is empty")