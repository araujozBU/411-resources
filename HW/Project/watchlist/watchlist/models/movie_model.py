import logging

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from watchlist.db import db
from watchlist.utils.logger import configure_logger
from watchlist.utils.api_utils import get_random

logger = logging.getLogger(__name__)
configure_logger(logger)


class Movies(db.Model):
    """
    Represents a movie in the catalog.

    This model maps to the 'Movies' table and stores metadata such as director,
    title, genre, release year, and duration. It also tracks play count.

    Used in a Flask-SQLAlchemy application for watchlist management,
    user interaction, and data-driven movie operations.
    """

    __tablename__ = "Movies"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    director = db.Column(db.String, nullable=False)
    title = db.Column(db.String, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    genre = db.Column(db.String, nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    play_count = db.Column(db.Integer, nullable=False, default=0)

    def validate(self) -> None:
        """
        Validates the movie instance before committing to the database.

        Raises:
            ValueError: If any required fields are invalid.
        """
        if not self.director or not isinstance(self.director, str):
            raise ValueError("Director must be a non-empty string.")
        if not self.title or not isinstance(self.title, str):
            raise ValueError("Title must be a non-empty string.")
        if not isinstance(self.year, int) or self.year <= 1900:
            raise ValueError("Year must be an integer greater than 1900.")
        if not self.genre or not isinstance(self.genre, str):
            raise ValueError("Genre must be a non-empty string.")
        if not isinstance(self.duration, int) or self.duration <= 0:
            raise ValueError("Duration must be a positive integer.")

    @classmethod
    def create_movie(cls, director: str, title: str, year: int, genre: str, duration: int) -> None:
        """
        Creates a new movie in the Movies table using SQLAlchemy.

        Args:
            director (str): The director's name.
            title (str): The movie title.
            year (int): The year the movie was released.
            genre (str): The movie genre.
            duration (int): The duration of the movie in seconds.

        Raises:
            ValueError: If any field is invalid or if a movie with the same compound key already exists.
            SQLAlchemyError: For any other database-related issues.
        """
        logger.info(f"Received request to create movie: {director} - {title} ({year})")

        try:
            movie = cls(
                director=director.strip(),
                title=title.strip(),
                year=year,
                genre=genre.strip(),
                duration=duration
            )
            movie.validate()
        except ValueError as e:
            logger.warning(f"Validation failed: {e}")
            raise

        try:
            existing = db.session.query(cls).filter_by(
                director=director.strip(), title=title.strip(), year=year
            ).first()
            if existing:
                logger.error(f"Movie already exists: {director} - {title} ({year})")
                raise ValueError(
                    f"Movie with director '{director}', title '{title}', and year {year} already exists."
                )

            db.session.add(movie)
            db.session.commit()
            logger.info(f"Movie successfully added: {director} - {title} ({year})")

        except IntegrityError:
            logger.error(f"Movie already exists: {director} - {title} ({year})")
            db.session.rollback()
            raise ValueError(
                f"Movie with director '{director}', title '{title}', and year {year} already exists."
            )

        except SQLAlchemyError as e:
            logger.error(f"Database error while creating movie: {e}")
            db.session.rollback()
            raise

    @classmethod
    def delete_movie(cls, movie_id: int) -> None:
        """
        Permanently deletes a movie from the catalog by ID.

        Args:
            movie_id (int): The ID of the movie to delete.

        Raises:
            ValueError: If the movie with the given ID does not exist.
            SQLAlchemyError: For any database-related issues.
        """
        logger.info(f"Received request to delete movie with ID {movie_id}")

        try:
            movie = db.session.get(cls, movie_id)
            if not movie:
                logger.warning(f"Attempted to delete non-existent movie with ID {movie_id}")
                raise ValueError(f"Movie with ID {movie_id} not found")

            db.session.delete(movie)
            db.session.commit()
            logger.info(f"Successfully deleted movie with ID {movie_id}")

        except SQLAlchemyError as e:
            logger.error(f"Database error while deleting movie with ID {movie_id}: {e}")
            db.session.rollback()
            raise

    @classmethod
    def get_movie_by_id(cls, movie_id: int) -> "Movies":
        """
        Retrieves a movie from the catalog by its ID.

        Args:
            movie_id (int): The ID of the movie to retrieve.

        Returns:
            Movies: The movie instance corresponding to the ID.

        Raises:
            ValueError: If no movie with the given ID is found.
            SQLAlchemyError: If a database error occurs.
        """
        logger.info(f"Attempting to retrieve movie with ID {movie_id}")

        try:
            movie = db.session.get(cls, movie_id)
            if not movie:
                logger.info(f"Movie with ID {movie_id} not found")
                raise ValueError(f"Movie with ID {movie_id} not found")

            logger.info(f"Successfully retrieved movie: {movie.director} - {movie.title} ({movie.year})")
            return movie

        except SQLAlchemyError as e:
            logger.error(f"Database error while retrieving movie by ID {movie_id}: {e}")
            raise

    @classmethod
    def get_movie_by_compound_key(cls, director: str, title: str, year: int) -> "Movies":
        """
        Retrieves a movie from the catalog by its compound key (director, title, year).

        Args:
            director (str): The director of the movie.
            title (str): The title of the movie.
            year (int): The year the movie was released.

        Returns:
            Movies: The movie instance matching the provided compound key.

        Raises:
            ValueError: If no matching movie is found.
            SQLAlchemyError: If a database error occurs.
        """
        logger.info(f"Attempting to retrieve movie with director '{director}', title '{title}', and year {year}")

        try:
            movie = db.session.query(cls).filter_by(
                director=director.strip(), title=title.strip(), year=year
            ).first()

            if not movie:
                logger.info(
                    f"Movie with director '{director}', title '{title}', and year {year} not found"
                )
                raise ValueError(
                    f"Movie with director '{director}', title '{title}', and year {year} not found"
                )

            logger.info(f"Successfully retrieved movie: {movie.director} - {movie.title} ({movie.year})")
            return movie

        except SQLAlchemyError as e:
            logger.error(
                f"Database error while retrieving movie by compound key"
                f" (director '{director}', title '{title}', year {year}): {e}"
            )
            raise

    @classmethod
    def get_all_movies(cls, sort_by_play_count: bool = False) -> list[dict]:
        """
        Retrieves all movies from the catalog as dictionaries.

        Args:
            sort_by_play_count (bool): If True, sort the movies by play count in descending order.

        Returns:
            list[dict]: A list of dictionaries representing all movies with play_count.

        Raises:
            SQLAlchemyError: If any database error occurs.
        """
        logger.info("Attempting to retrieve all movies from the catalog")

        try:
            query = db.session.query(cls)
            if sort_by_play_count:
                query = query.order_by(cls.play_count.desc())

            movies = query.all()
            if not movies:
                logger.warning("The movie catalog is empty.")
                return []

            results = [
                {
                    "id": m.id,
                    "director": m.director,
                    "title": m.title,
                    "year": m.year,
                    "genre": m.genre,
                    "duration": m.duration,
                    "play_count": m.play_count,
                }
                for m in movies
            ]

            logger.info(f"Retrieved {len(results)} movies from the catalog")
            return results

        except SQLAlchemyError as e:
            logger.error(f"Database error while retrieving all movies: {e}")
            raise

    @classmethod
    def get_random_movie(cls) -> dict:
        """
        Retrieves a random movie from the catalog as a dictionary.

        Returns:
            dict: A randomly selected movie dictionary.
        """
        all_movies = cls.get_all_movies()
        if not all_movies:
            logger.warning("Cannot retrieve random movie because the catalog is empty.")
            raise ValueError("The movie catalog is empty.")

        index = get_random(len(all_movies))
        logger.info(f"Random index selected: {index} (total movies: {len(all_movies)})")
        return all_movies[index - 1]

    def update_play_count(self) -> None:
        """
        Increments the play count of the current movie instance.

        Raises:
            ValueError: If the movie does not exist in the database.
            SQLAlchemyError: If any database error occurs.
        """
        logger.info(f"Attempting to update play count for movie with ID {self.id}")

        try:
            movie = db.session.get(Movies, self.id)
            if not movie:
                logger.warning(f"Cannot update play count: Movie with ID {self.id} not found.")
                raise ValueError(f"Movie with ID {self.id} not found")

            movie.play_count += 1
            db.session.commit()
            logger.info(f"Play count incremented for movie with ID: {self.id}")

        except SQLAlchemyError as e:
            logger.error(f"Database error while updating play count for movie with ID {self.id}: {e}")
            db.session.rollback()
            raise
