from dotenv import load_dotenv
from flask import Flask, jsonify, make_response, Response, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from config import ProductionConfig

from watchlist.db import db
from watchlist.models.movie_model import Movies
from watchlist.models.watchlist_model import WatchlistModel
from watchlist.models.user_model import Users
from watchlist.utils.logger import configure_logger


load_dotenv()


def create_app(config_class=ProductionConfig) -> Flask:
    """Create a Flask application with the specified configuration.

    Args:
        config_class (Config): The configuration class to use.

    Returns:
        Flask app: The configured Flask application.

    """
    app = Flask(__name__)
    configure_logger(app.logger)

    app.config.from_object(config_class)

    # Initialize database
    db.init_app(app)
    with app.app_context():
        db.create_all()

    # Initialize login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        return Users.query.filter_by(username=user_id).first()

    @login_manager.unauthorized_handler
    def unauthorized():
        return make_response(jsonify({
            "status": "error",
            "message": "Authentication required"
        }), 401)

    watchlist_model = WatchlistModel()

    @app.route('/api/health', methods=['GET'])
    def healthcheck() -> Response:
        """Health check route to verify the service is running.

        Returns:
            JSON response indicating the health status of the service.

        """
        app.logger.info("Health check endpoint hit")
        return make_response(jsonify({
            'status': 'success',
            'message': 'Service is running'
        }), 200)

    ##########################################################
    #
    # User Management
    #
    #########################################################

    @app.route('/api/create-user', methods=['PUT'])
    def create_user() -> Response:
        """Register a new user account.

        Expected JSON Input:
            - username (str): The desired username.
            - password (str): The desired password.

        Returns:
            JSON response indicating the success of the user creation.

        Raises:
            400 error if the username or password is missing.
            500 error if there is an issue creating the user in the database.
        """
        try:
            data = request.get_json()
            username = data.get("username")
            password = data.get("password")

            if not username or not password:
                return make_response(jsonify({
                    "status": "error",
                    "message": "Username and password are required"
                }), 400)

            Users.create_user(username, password)
            return make_response(jsonify({
                "status": "success",
                "message": f"User '{username}' created successfully"
            }), 201)

        except ValueError as e:
            return make_response(jsonify({
                "status": "error",
                "message": str(e)
            }), 400)
        except Exception as e:
            app.logger.error(f"User creation failed: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while creating user",
                "details": str(e)
            }), 500)

    @app.route('/api/login', methods=['POST'])
    def login() -> Response:
        """Authenticate a user and log them in.

        Expected JSON Input:
            - username (str): The username of the user.
            - password (str): The password of the user.

        Returns:
            JSON response indicating the success of the login attempt.

        Raises:
            401 error if the username or password is incorrect.
        """
        try:
            data = request.get_json()
            username = data.get("username")
            password = data.get("password")

            if not username or not password:
                return make_response(jsonify({
                    "status": "error",
                    "message": "Username and password are required"
                }), 400)

            if Users.check_password(username, password):
                user = Users.query.filter_by(username=username).first()
                login_user(user)
                return make_response(jsonify({
                    "status": "success",
                    "message": f"User '{username}' logged in successfully"
                }), 200)
            else:
                return make_response(jsonify({
                    "status": "error",
                    "message": "Invalid username or password"
                }), 401)

        except ValueError as e:
            return make_response(jsonify({
                "status": "error",
                "message": str(e)
            }), 401)
        except Exception as e:
            app.logger.error(f"Login failed: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred during login",
                "details": str(e)
            }), 500)

    @app.route('/api/logout', methods=['POST'])
    @login_required
    def logout() -> Response:
        """Log out the current user.

        Returns:
            JSON response indicating the success of the logout operation.

        """
        logout_user()
        return make_response(jsonify({
            "status": "success",
            "message": "User logged out successfully"
        }), 200)

    @app.route('/api/change-password', methods=['POST'])
    @login_required
    def change_password() -> Response:
        """Change the password for the current user.

        Expected JSON Input:
            - new_password (str): The new password to set.

        Returns:
            JSON response indicating the success of the password change.

        Raises:
            400 error if the new password is not provided.
            500 error if there is an issue updating the password in the database.
        """
        try:
            data = request.get_json()
            new_password = data.get("new_password")

            if not new_password:
                return make_response(jsonify({
                    "status": "error",
                    "message": "New password is required"
                }), 400)

            username = current_user.username
            Users.update_password(username, new_password)
            return make_response(jsonify({
                "status": "success",
                "message": "Password changed successfully"
            }), 200)

        except ValueError as e:
            return make_response(jsonify({
                "status": "error",
                "message": str(e)
            }), 400)
        except Exception as e:
            app.logger.error(f"Password change failed: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while changing password",
                "details": str(e)
            }), 500)

    @app.route('/api/reset-users', methods=['DELETE'])
    def reset_users() -> Response:
        """Recreate the users table to delete all users.

        Returns:
            JSON response indicating the success of recreating the Users table.

        Raises:
            500 error if there is an issue recreating the Users table.
        """
        try:
            app.logger.info("Received request to recreate Users table")
            with app.app_context():
                Users.__table__.drop(db.engine)
                Users.__table__.create(db.engine)
            app.logger.info("Users table recreated successfully")
            return make_response(jsonify({
                "status": "success",
                "message": f"Users table recreated successfully"
            }), 200)

        except Exception as e:
            app.logger.error(f"Users table recreation failed: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while deleting users",
                "details": str(e)
            }), 500)

    ##########################################################
    #
    # Movies
    #
    ##########################################################

    @app.route('/api/reset-movies', methods=['DELETE'])
    def reset_movie() -> Response:
        """Recreate the movie table to delete movie.

        Returns:
            JSON response indicating the success of recreating the Movies table.

        Raises:
            500 error if there is an issue recreating the Movies table.
        """
        try:
            app.logger.info("Received request to recreate Movies table")
            with app.app_context():
                Movies.__table__.drop(db.engine)
                Movies.__table__.create(db.engine)
            app.logger.info("Movies table recreated successfully")
            return make_response(jsonify({
                "status": "success",
                "message": f"Movies table recreated successfully"
            }), 200)

        except Exception as e:
            app.logger.error(f"Movies table recreation failed: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while deleting users",
                "details": str(e)
            }), 500)


    @app.route('/api/create-movie', methods=['POST'])
    @login_required
    def add_movie() -> Response:
        """Route to add a new movie to the catalog.

        Expected JSON Input:
            - director (str): The director's name.
            - title (str): The movie title.
            - year (int): The year the movie was released.
            - genre (str): The genre of the movie.
            - duration (int): The duration of the movie in seconds.

        Returns:
            JSON response indicating the success of the movie addition.

        Raises:
            400 error if input validation fails.
            500 error if there is an issue adding the movie to the watchlist.

        """
        app.logger.info("Received request to add a new movie")

        try:
            data = request.get_json()

            required_fields = ["director", "title", "year", "genre", "duration"]
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                app.logger.warning(f"Missing required fields: {missing_fields}")
                return make_response(jsonify({
                    "status": "error",
                    "message": f"Missing required fields: {', '.join(missing_fields)}"
                }), 400)

            director = data["director"]
            title = data["title"]
            year = data["year"]
            genre = data["genre"]
            duration = data["duration"]

            if (
                not isinstance(director, str)
                or not isinstance(title, str)
                or not isinstance(year, int)
                or not isinstance(genre, str)
                or not isinstance(duration, int)
            ):
                app.logger.warning("Invalid input data types")
                return make_response(jsonify({
                    "status": "error",
                    "message": "Invalid input types: director/title/genre should be strings, year and duration should be integers"
                }), 400)

            app.logger.info(f"Adding movie: {director} - {title} ({year}), Genre: {genre}, Duration: {duration}s")
            Movies.create_movie(director=director, title=title, year=year, genre=genre, duration=duration)

            app.logger.info(f"Movie added successfully: {director} - {title}")
            return make_response(jsonify({
                "status": "success",
                "message": f"Movie '{title}' by {director} added successfully"
            }), 201)

        except Exception as e:
            app.logger.error(f"Failed to add movie: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while adding the movie",
                "details": str(e)
            }), 500)


    @app.route('/api/delete-movie/<int:song_id>', methods=['DELETE'])
    @login_required
    def delete_movie(movie_id: int) -> Response:
        """Route to delete a movie by ID.

        Path Parameter:
            - song_id (int): The ID of the movie to delete.

        Returns:
            JSON response indicating success of the operation.

        Raises:
            400 error if the movie does not exist.
            500 error if there is an issue removing the movie from the database.

        """
        try:
            app.logger.info(f"Received request to delete movie with ID {movie_id}")

            # Check if the movie exists before attempting to delete
            movie = Movies.get_song_by_id(movie_id)
            if not movie:
                app.logger.warning(f"Movie with ID {movie_id} not found.")
                return make_response(jsonify({
                    "status": "error",
                    "message": f"Movie with ID {movie_id} not found"
                }), 400)

            Movies.delete_movie(movie_id)
            app.logger.info(f"Successfully deleted movie with ID {movie_id}")

            return make_response(jsonify({
                "status": "success",
                "message": f"Movie with ID {movie_id} deleted successfully"
            }), 200)

        except Exception as e:
            app.logger.error(f"Failed to delete movie: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while deleting the movie",
                "details": str(e)
            }), 500)


    @app.route('/api/get-all-movie-from-catalog', methods=['GET'])
    @login_required
    def get_all_movies() -> Response:
        """Route to retrieve all movie in the catalog (non-deleted), with an option to sort by play count.

        Query Parameter:
            - sort_by_play_count (bool, optional): If true, sort movie by play count.

        Returns:
            JSON response containing the list of movie.

        Raises:
            500 error if there is an issue retrieving movie from the catalog.

        """
        try:
            # Extract query parameter for sorting by play count
            sort_by_play_count = request.args.get('sort_by_play_count', 'false').lower() == 'true'

            app.logger.info(f"Received request to retrieve all movie from catalog (sort_by_play_count={sort_by_play_count})")

            movie = Movies.get_all_movie(sort_by_play_count=sort_by_play_count)

            app.logger.info(f"Successfully retrieved {len(movie)} movie from the catalog")

            return make_response(jsonify({
                "status": "success",
                "message": "Movies retrieved successfully",
                "movie": movie
            }), 200)

        except Exception as e:
            app.logger.error(f"Failed to retrieve movie: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while retrieving movie",
                "details": str(e)
            }), 500)


    @app.route('/api/get-movie-from-catalog-by-id/<int:song_id>', methods=['GET'])
    @login_required
    def get_movie_by_id(song_id: int) -> Response:
        """Route to retrieve a movie by its ID.

        Path Parameter:
            - song_id (int): The ID of the movie.

        Returns:
            JSON response containing the movie details.

        Raises:
            400 error if the movie does not exist.
            500 error if there is an issue retrieving the movie.

        """
        try:
            app.logger.info(f"Received request to retrieve movie with ID {song_id}")

            movie = Movies.get_movie_by_id(song_id)
            if not movie:
                app.logger.warning(f"Movie with ID {song_id} not found.")
                return make_response(jsonify({
                    "status": "error",
                    "message": f"Movie with ID {song_id} not found"
                }), 400)

            app.logger.info(f"Successfully retrieved movie: {movie.title} by {movie.director} (ID {song_id})")

            return make_response(jsonify({
                "status": "success",
                "message": "Movie retrieved successfully",
                "movie": movie
            }), 200)

        except Exception as e:
            app.logger.error(f"Failed to retrieve movie by ID: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while retrieving the movie",
                "details": str(e)
            }), 500)


    @app.route('/api/get-movie-from-catalog-by-compound-key', methods=['GET'])
    @login_required
    def get_movie_by_compound_key() -> Response:
        """Route to retrieve a movie by its compound key (director, title, year).

        Query Parameters:
            - director (str): The director's name.
            - title (str): The movie title.
            - year (int): The year the movie was released.

        Returns:
            JSON response containing the movie details.

        Raises:
            400 error if required query parameters are missing or invalid.
            500 error if there is an issue retrieving the movie.

        """
        try:
            director = request.args.get('director')
            title = request.args.get('title')
            year = request.args.get('year')

            if not director or not title or not year:
                app.logger.warning("Missing required query parameters: director, title, year")
                return make_response(jsonify({
                    "status": "error",
                    "message": "Missing required query parameters: director, title, year"
                }), 400)

            try:
                year = int(year)
            except ValueError:
                app.logger.warning(f"Invalid year format: {year}. Year must be an integer.")
                return make_response(jsonify({
                    "status": "error",
                    "message": "Year must be an integer"
                }), 400)

            app.logger.info(f"Received request to retrieve movie by compound key: {director}, {title}, {year}")

            movie = Movies.get_movie_by_compound_key(director, title, year)
            if not movie:
                app.logger.warning(f"Movie not found: {director} - {title} ({year})")
                return make_response(jsonify({
                    "status": "error",
                    "message": f"Movie not found: {director} - {title} ({year})"
                }), 400)

            app.logger.info(f"Successfully retrieved movie: {movie.title} by {movie.director} ({year})")

            return make_response(jsonify({
                "status": "success",
                "message": "Movie retrieved successfully",
                "movie": movie
            }), 200)

        except Exception as e:
            app.logger.error(f"Failed to retrieve movie by compound key: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while retrieving the movie",
                "details": str(e)
            }), 500)


    @app.route('/api/get-random-movie', methods=['GET'])
    @login_required
    def get_random_movie() -> Response:
        """Route to retrieve a random movie from the catalog.

        Returns:
            JSON response containing the details of a random movie.

        Raises:
            400 error if no movie exist in the catalog.
            500 error if there is an issue retrieving the movie

        """
        try:
            app.logger.info("Received request to retrieve a random movie from the catalog")

            movie = Movies.get_random_movie()
            if not movie:
                app.logger.warning("No movie found in the catalog.")
                return make_response(jsonify({
                    "status": "error",
                    "message": "No movie available in the catalog"
                }), 400)

            app.logger.info(f"Successfully retrieved random movie: {movie.title} by {movie.director}")

            return make_response(jsonify({
                "status": "success",
                "message": "Random movie retrieved successfully",
                "movie": movie
            }), 200)

        except Exception as e:
            app.logger.error(f"Failed to retrieve random movie: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while retrieving a random movie",
                "details": str(e)
            }), 500)


    ############################################################
    #
    # watchlist Add / Remove
    #
    ############################################################

    @app.route('/api/add-movie-to-watchlist', methods=['POST'])
    @login_required
    def add_movie_to_watchlist() -> Response:
        """Route to add a movie to the watchlist by compound key (director, title, year)."""
        try:
            data = request.get_json() or {}
            required = ["director", "title", "year"]
            missing = [f for f in required if f not in data]
            if missing:
                return make_response(jsonify({
                    "status": "error",
                    "message": f"Missing required fields: {', '.join(missing)}"
                }), 400)

            director = data["director"]
            title = data["title"]
            try:
                year = int(data["year"])
            except ValueError:
                return make_response(jsonify({
                    "status": "error",
                    "message": "Year must be a valid integer"
                }), 400)

            app.logger.info(f"Looking up movie: {director} - {title} ({year})")
            movie = Movies.get_movie_by_compound_key(director, title, year)

            watchlist_model.add_movie_to_watchlist(movie.id)

            app.logger.info(f"Successfully added movie to watchlist: {director} - {title} ({year})")
            return make_response(jsonify({
                "status": "success",
                "message": f"Movie '{title}' by {director} ({year}) added to watchlist"
            }), 201)

        except ValueError as e:
            # covers both lookup failures and duplicate‐entries
            return make_response(jsonify({
                "status": "error",
                "message": str(e)
            }), 400)

        except Exception as e:
            app.logger.error(f"Failed to add movie to watchlist: {e}", exc_info=True)
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while adding the movie to the watchlist",
                "details": str(e)
            }), 500)

    @app.route('/api/remove-movie-from-watchlist', methods=['DELETE'])
    @login_required
    def remove_song_by_song_id() -> Response:
        """Route to remove a movie from the watchlist by compound key (director, title, year).

        Expected JSON Input:
            - director (str): The director's name.
            - title (str): The movie title.
            - year (int): The year the movie was released.

        Returns:
            JSON response indicating success of the removal.

        Raises:
            400 error if required fields are missing or the movie does not exist in the watchlist.
            500 error if there is an issue removing the movie.

        """
        try:
            app.logger.info("Received request to remove movie from watchlist")

            data = request.get_json()
            required_fields = ["director", "title", "year"]
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                app.logger.warning(f"Missing required fields: {missing_fields}")
                return make_response(jsonify({
                    "status": "error",
                    "message": f"Missing required fields: {', '.join(missing_fields)}"
                }), 400)

            director = data["director"]
            title = data["title"]

            try:
                year = int(data["year"])
            except ValueError:
                app.logger.warning(f"Invalid year format: {data['year']}")
                return make_response(jsonify({
                    "status": "error",
                    "message": "Year must be a valid integer"
                }), 400)

            app.logger.info(f"Looking up movie to remove: {director} - {title} ({year})")
            movie = Movies.get_song_by_compound_key(director, title, year)

            if not movie:
                app.logger.warning(f"Movie not found in catalog: {director} - {title} ({year})")
                return make_response(jsonify({
                    "status": "error",
                    "message": f"Movie '{title}' by {director} ({year}) not found in catalog"
                }), 400)

            watchlist_model.remove_song_by_song_id(movie.id)
            app.logger.info(f"Successfully removed movie from watchlist: {director} - {title} ({year})")

            return make_response(jsonify({
                "status": "success",
                "message": f"Movie '{title}' by {director} ({year}) removed from watchlist"
            }), 200)

        except Exception as e:
            app.logger.error(f"Failed to remove movie from watchlist: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while removing the movie from the watchlist",
                "details": str(e)
            }), 500)


    @app.route('/api/remove-movie-from-watchlist-by-movie-number/<int:movie_number>', methods=['DELETE'])
    @login_required
    def remove_movie_by_movie_number(movie_number: int) -> Response:
        """Route to remove a movie from the watchlist by movie number.

        Path Parameter:
            - movie_number (int): The movie number of the movie to remove.

        Returns:
            JSON response indicating success of the removal.

        Raises:
            404 error if the movie number does not exist.
            500 error if there is an issue removing the movie.

        """
        try:
            app.logger.info(f"Received request to remove movie at movie number {movie_number} from watchlist")

            watchlist_model.remove_movie_by_movie_number(movie_number)

            app.logger.info(f"Successfully removed movie at movie number {movie_number} from watchlist")
            return make_response(jsonify({
                "status": "success",
                "message": f"Movie at movie number {movie_number} removed from watchlist"
            }), 200)

        except ValueError as e:
            app.logger.warning(f"Movie number {movie_number} not found in watchlist: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": f"Movie number {movie_number} not found in watchlist"
            }), 404)

        except Exception as e:
            app.logger.error(f"Failed to remove movie at movie number {movie_number}: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while removing the movie from the watchlist",
                "details": str(e)
            }), 500)


    @app.route('/api/clear-watchlist', methods=['POST'])
    @login_required
    def clear_watchlist() -> Response:
        """Route to clear all movie from the watchlist.

        Returns:
            JSON response indicating success of the operation.

        Raises:
            500 error if there is an issue clearing the watchlist.

        """
        try:
            app.logger.info("Received request to clear the watchlist")

            watchlist_model.clear_watchlist()

            app.logger.info("Successfully cleared the watchlist")
            return make_response(jsonify({
                "status": "success",
                "message": "Watchlist cleared"
            }), 200)

        except Exception as e:
            app.logger.error(f"Failed to clear watchlist: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while clearing the watchlist",
                "details": str(e)
            }), 500)


    ############################################################
    #
    # Play watchlist
    #
    ############################################################


    @app.route('/api/play-current-movie', methods=['POST'])
    @login_required
    def play_current_song() -> Response:
        """Route to play the current movie in the watchlist.

        Returns:
            JSON response indicating success of the operation.

        Raises:
            404 error if there is no current movie.
            500 error if there is an issue playing the current movie.

        """
        try:
            app.logger.info("Received request to play the current movie")

            current_song = watchlist_model.get_current_song()
            if not current_song:
                app.logger.warning("No current movie found in the watchlist")
                return make_response(jsonify({
                    "status": "error",
                    "message": "No current movie found in the watchlist"
                }), 404)

            watchlist_model.play_current_song()
            app.logger.info(f"Now playing: {current_song.director} - {current_song.title} ({current_song.year})")

            return make_response(jsonify({
                "status": "success",
                "message": "Now playing current movie",
                "movie": {
                    "id": current_song.id,
                    "director": current_song.director,
                    "title": current_song.title,
                    "year": current_song.year,
                    "genre": current_song.genre,
                    "duration": current_song.duration
                }
            }), 200)

        except Exception as e:
            app.logger.error(f"Failed to play current movie: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while playing the current movie",
                "details": str(e)
            }), 500)


    @app.route('/api/play-entire-watchlist', methods=['POST'])
    @login_required
    def play_entire_watchlist() -> Response:
        """Route to play all movie in the watchlist.

        Returns:
            JSON response indicating success of the operation.

        Raises:
            400 error if the watchlist is empty.
            500 error if there is an issue playing the watchlist.

        """
        try:
            app.logger.info("Received request to play the entire watchlist")

            if watchlist_model.check_if_empty():
                app.logger.warning("Cannot play watchlist: No movie available")
                return make_response(jsonify({
                    "status": "error",
                    "message": "Cannot play watchlist: No movie available"
                }), 400)

            watchlist_model.play_entire_playlist()
            app.logger.info("Playing entire watchlist")

            return make_response(jsonify({
                "status": "success",
                "message": "Playing entire watchlist"
            }), 200)

        except Exception as e:
            app.logger.error(f"Failed to play entire watchlist: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while playing the watchlist",
                "details": str(e)
            }), 500)


    @app.route('/api/play-rest-of-watchlist', methods=['POST'])
    @login_required
    def play_rest_of_playlist() -> Response:
        """Route to play the rest of the watchlist from the current movie.

        Returns:
            JSON response indicating success of the operation.

        Raises:
            400 error if the watchlist is empty or if no current movie is playing.
            500 error if there is an issue playing the rest of the watchlist.

        """
        try:
            app.logger.info("Received request to play the rest of the watchlist")

            if watchlist_model.check_if_empty():
                app.logger.warning("Cannot play rest of watchlist: No movie available")
                return make_response(jsonify({
                    "status": "error",
                    "message": "Cannot play rest of watchlist: No movie available"
                }), 400)

            if not watchlist_model.get_current_song():
                app.logger.warning("No current movie playing. Cannot continue watchlist.")
                return make_response(jsonify({
                    "status": "error",
                    "message": "No current movie playing. Cannot continue watchlist."
                }), 400)

            watchlist_model.play_rest_of_playlist()
            app.logger.info("Playing rest of the watchlist")

            return make_response(jsonify({
                "status": "success",
                "message": "Playing rest of the watchlist"
            }), 200)

        except Exception as e:
            app.logger.error(f"Failed to play rest of the watchlist: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while playing the rest of the watchlist",
                "details": str(e)
            }), 500)


    @app.route('/api/rewind-watchlist', methods=['POST'])
    @login_required
    def rewind_playlist() -> Response:
        """Route to rewind the watchlist to the first movie.

        Returns:
            JSON response indicating success of the operation.

        Raises:
            400 error if the watchlist is empty.
            500 error if there is an issue rewinding the watchlist.

        """
        try:
            app.logger.info("Received request to rewind the watchlist")

            if watchlist_model.check_if_empty():
                app.logger.warning("Cannot rewind: No movie in watchlist")
                return make_response(jsonify({
                    "status": "error",
                    "message": "Cannot rewind: No movie in watchlist"
                }), 400)

            watchlist_model.rewind_playlist()
            app.logger.info("Watchlist successfully rewound to the first movie")

            return make_response(jsonify({
                "status": "success",
                "message": "Watchlist rewound to the first movie"
            }), 200)

        except Exception as e:
            app.logger.error(f"Failed to rewind watchlist: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while rewinding the watchlist",
                "details": str(e)
            }), 500)


    @app.route('/api/go-to-movie-number/<int:movie_number>', methods=['POST'])
    @login_required
    def go_to_track_number(movie_number: int) -> Response:
        """Route to set the watchlist to start playing from a specific movie number.

        Path Parameter:
            - movie_number (int): The movie number to set as the current movie.

        Returns:
            JSON response indicating success or an error message.

        Raises:
            400 error if the movie number is invalid.
            500 error if there is an issue updating the movie number.
        """
        try:
            app.logger.info(f"Received request to go to movie number {movie_number}")

            if not watchlist_model.is_valid_track_number(movie_number):
                app.logger.warning(f"Invalid movie number: {movie_number}")
                return make_response(jsonify({
                    "status": "error",
                    "message": f"Invalid movie number: {movie_number}. Please provide a valid movie number."
                }), 400)

            watchlist_model.go_to_track_number(movie_number)
            app.logger.info(f"Watchlist set to movie number {movie_number}")

            return make_response(jsonify({
                "status": "success",
                "message": f"Now playing from movie number {movie_number}"
            }), 200)

        except ValueError as e:
            app.logger.warning(f"Failed to set movie number {movie_number}: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": str(e)
            }), 400)

        except Exception as e:
            app.logger.error(f"Internal error while going to movie number {movie_number}: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while changing the movie number",
                "details": str(e)
            }), 500)


    @app.route('/api/go-to-random-movie', methods=['POST'])
    @login_required
    def go_to_random_track() -> Response:
        """Route to set the watchlist to start playing from a random movie number.

        Returns:
            JSON response indicating success or an error message.

        Raises:
            400 error if the watchlist is empty.
            500 error if there is an issue selecting a random movie.

        """
        try:
            app.logger.info("Received request to go to a random movie")

            if watchlist_model.get_playlist_length() == 0:
                app.logger.warning("Attempted to go to a random movie but the watchlist is empty")
                return make_response(jsonify({
                    "status": "error",
                    "message": "Cannot select a random movie. The watchlist is empty."
                }), 400)

            watchlist_model.go_to_random_track()
            app.logger.info(f"Watchlist set to random movie number {watchlist_model.current_track_number}")

            return make_response(jsonify({
                "status": "success",
                "message": f"Now playing from random movie number {watchlist_model.current_track_number}"
            }), 200)

        except Exception as e:
            app.logger.error(f"Internal error while selecting a random movie: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while selecting a random movie",
                "details": str(e)
            }), 500)


    ############################################################
    #
    # View Watchlist
    #
    ############################################################

    @app.route('/api/get-all-movie-from-watchlist', methods=['GET'])
    @login_required
    def get_all_movie_from_watchlist() -> Response:
        """Retrieve all movies in the watchlist."""
        try:
            app.logger.info("Received request to retrieve all movies from the watchlist.")
            
            # fetch the list of Movies objects
            movies = watchlist_model.get_all_movies()

            # convert each Movies object into a plain dict
            watchlist = []
            for m in movies:
                watchlist.append({
                    "id":       m.id,
                    "director": m.director,
                    "title":    m.title,
                    "year":     m.year,
                    "genre":    m.genre,
                    "duration": m.duration,
                })

            app.logger.info(f"Successfully retrieved {len(watchlist)} movies from the watchlist.")
            return make_response(jsonify({
                "status":    "success",
                "watchlist": watchlist
            }), 200)

        except Exception as e:
            app.logger.error("Failed to retrieve watchlist", exc_info=True)
            return make_response(jsonify({
                "status":  "error",
                "message": "An internal error occurred while retrieving the watchlist",
                "details": str(e)
            }), 500)


    @app.route('/api/get-movie-from-watchlist-by-movie-number/<int:movie_number>', methods=['GET'])
    @login_required
    def get_movie_by_movie_number(movie_number: int) -> Response:
        """Retrieve a movie from the watchlist by movie number.

        Path Parameter:
            - movie_number (int): The movie number of the movie.

        Returns:
            JSON response containing movie details.

        Raises:
            404 error if the movie number is not found.
            500 error if there is an issue retrieving the movie.

        """
        try:
            app.logger.info(f"Received request to retrieve movie at movie number {movie_number}.")

            movie = watchlist_model.get_movie_by_movie_number(movie_number)

            app.logger.info(f"Successfully retrieved movie: {movie.director} - {movie.title} (Track {movie_number}).")
            return make_response(jsonify({
                "status": "success",
                "movie": movie
            }), 200)

        except ValueError as e:
            app.logger.warning(f"Track number {movie_number} not found: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": str(e)
            }), 404)

        except Exception as e:
            app.logger.error(f"Failed to retrieve movie by movie number {movie_number}: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while retrieving the movie",
                "details": str(e)
            }), 500)


    @app.route('/api/get-current-movie', methods=['GET'])
    @login_required
    def get_current_song() -> Response:
        """Retrieve the current movie being played.

        Returns:
            JSON response containing current movie details.

        Raises:
            500 error if there is an issue retrieving the current movie.

        """
        try:
            app.logger.info("Received request to retrieve the current movie.")

            current_song = watchlist_model.get_current_song()

            app.logger.info(f"Successfully retrieved current movie: {current_song.director} - {current_song.title}.")
            return make_response(jsonify({
                "status": "success",
                "current_song": current_song
            }), 200)

        except Exception as e:
            app.logger.error(f"Failed to retrieve current movie: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while retrieving the current movie",
                "details": str(e)
            }), 500)


    @app.route('/api/get-watchlist-length-duration', methods=['GET'])
    @login_required
    def get_playlist_length_and_duration() -> Response:
        """Retrieve the length (number of movie) and total duration of the watchlist.

        Returns:
            JSON response containing the watchlist length and total duration.

        Raises:
            500 error if there is an issue retrieving watchlist information.

        """
        try:
            app.logger.info("Received request to retrieve watchlist length and duration.")

            playlist_length = watchlist_model.get_playlist_length()
            playlist_duration = watchlist_model.get_playlist_duration()

            app.logger.info(f"Watchlist contains {playlist_length} movie with a total duration of {playlist_duration} seconds.")
            return make_response(jsonify({
                "status": "success",
                "playlist_length": playlist_length,
                "playlist_duration": playlist_duration
            }), 200)

        except Exception as e:
            app.logger.error(f"Failed to retrieve watchlist length and duration: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while retrieving watchlist details",
                "details": str(e)
            }), 500)


    ############################################################
    #
    # Arrange Watchlist
    #
    ############################################################


    @app.route('/api/move-movie-to-beginning', methods=['POST'])
    @login_required
    def move_song_to_beginning() -> Response:
        """Move a movie to the beginning of the watchlist.

        Expected JSON Input:
            - director (str): The director of the movie.
            - title (str): The title of the movie.
            - year (int): The year the movie was released.

        Returns:
            Response: JSON response indicating success or an error message.

        Raises:
            400 error if required fields are missing.
            500 error if an error occurs while updating the watchlist.

        """
        try:
            data = request.get_json()

            required_fields = ["director", "title", "year"]
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                app.logger.warning(f"Missing required fields: {missing_fields}")
                return make_response(jsonify({
                    "status": "error",
                    "message": f"Missing required fields: {', '.join(missing_fields)}"
                }), 400)

            director, title, year = data["director"], data["title"], data["year"]
            app.logger.info(f"Received request to move movie to beginning: {director} - {title} ({year})")

            movie = Movies.get_song_by_compound_key(director, title, year)
            watchlist_model.move_song_to_beginning(movie.id)

            app.logger.info(f"Successfully moved movie to beginning: {director} - {title} ({year})")
            return make_response(jsonify({
                "status": "success",
                "message": f"Movie '{title}' by {director} moved to beginning"
            }), 200)

        except Exception as e:
            app.logger.error(f"Failed to move movie to beginning: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while moving the movie",
                "details": str(e)
            }), 500)


    @app.route('/api/move-movie-to-end', methods=['POST'])
    @login_required
    def move_song_to_end() -> Response:
        """Move a movie to the end of the watchlist.

        Expected JSON Input:
            - director (str): The director of the movie.
            - title (str): The title of the movie.
            - year (int): The year the movie was released.

        Returns:
            Response: JSON response indicating success or an error message.

        Raises:
            400 error if required fields are missing.
            500 if an error occurs while updating the watchlist.

        """
        try:
            data = request.get_json()

            required_fields = ["director", "title", "year"]
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                app.logger.warning(f"Missing required fields: {missing_fields}")
                return make_response(jsonify({
                    "status": "error",
                    "message": f"Missing required fields: {', '.join(missing_fields)}"
                }), 400)

            director, title, year = data["director"], data["title"], data["year"]
            app.logger.info(f"Received request to move movie to end: {director} - {title} ({year})")

            movie = Movies.get_song_by_compound_key(director, title, year)
            watchlist_model.move_song_to_end(movie.id)

            app.logger.info(f"Successfully moved movie to end: {director} - {title} ({year})")
            return make_response(jsonify({
                "status": "success",
                "message": f"Movie '{title}' by {director} moved to end"
            }), 200)

        except Exception as e:
            app.logger.error(f"Failed to move movie to end: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while moving the movie",
                "details": str(e)
            }), 500)


    @app.route('/api/move-movie-to-movie-number', methods=['POST'])
    @login_required
    def move_song_to_track_number() -> Response:
        """Move a movie to a specific movie number in the watchlist.

        Expected JSON Input:
            - director (str): The director of the movie.
            - title (str): The title of the movie.
            - year (int): The year the movie was released.
            - movie_number (int): The new movie number to move the movie to.

        Returns:
            Response: JSON response indicating success or an error message.

        Raises:
            400 error if required fields are missing.
            500 error if an error occurs while updating the watchlist.
        """
        try:
            data = request.get_json()

            required_fields = ["director", "title", "year", "movie_number"]
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                app.logger.warning(f"Missing required fields: {missing_fields}")
                return make_response(jsonify({
                    "status": "error",
                    "message": f"Missing required fields: {', '.join(missing_fields)}"
                }), 400)

            director, title, year, movie_number = data["director"], data["title"], data["year"], data["movie_number"]
            app.logger.info(f"Received request to move movie to movie number {movie_number}: {director} - {title} ({year})")

            movie = Movies.get_song_by_compound_key(director, title, year)
            watchlist_model.move_song_to_track_number(movie.id, movie_number)

            app.logger.info(f"Successfully moved movie to movie {movie_number}: {director} - {title} ({year})")
            return make_response(jsonify({
                "status": "success",
                "message": f"Movie '{title}' by {director} moved to movie {movie_number}"
            }), 200)

        except Exception as e:
            app.logger.error(f"Failed to move movie to movie number: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while moving the movie",
                "details": str(e)
            }), 500)


    @app.route('/api/swap-movie-in-watchlist', methods=['POST'])
    @login_required
    def swap_movie_in_playlist() -> Response:
        """Swap two movie in the watchlist by their movie numbers.

        Expected JSON Input:
            - track_number_1 (int): The movie number of the first movie.
            - track_number_2 (int): The movie number of the second movie.

        Returns:
            Response: JSON response indicating success or an error message.

        Raises:
            400 error if required fields are missing.
            500 error if an error occurs while swapping movie in the watchlist.
        """
        try:
            data = request.get_json()

            required_fields = ["track_number_1", "track_number_2"]
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                app.logger.warning(f"Missing required fields: {missing_fields}")
                return make_response(jsonify({
                    "status": "error",
                    "message": f"Missing required fields: {', '.join(missing_fields)}"
                }), 400)

            track_number_1, track_number_2 = data["track_number_1"], data["track_number_2"]
            app.logger.info(f"Received request to swap movie at movie numbers {track_number_1} and {track_number_2}")

            song_1 = watchlist_model.get_song_by_track_number(track_number_1)
            song_2 = watchlist_model.get_song_by_track_number(track_number_2)
            watchlist_model.swap_movie_in_playlist(song_1.id, song_2.id)

            app.logger.info(f"Successfully swapped movie: {song_1.director} - {song_1.title} <-> {song_2.director} - {song_2.title}")
            return make_response(jsonify({
                "status": "success",
                "message": f"Swapped movie: {song_1.director} - {song_1.title} <-> {song_2.director} - {song_2.title}"
            }), 200)

        except Exception as e:
            app.logger.error(f"Failed to swap movie in watchlist: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while swapping movie",
                "details": str(e)
            }), 500)



    ############################################################
    #
    # Leaderboard / Stats
    #
    ############################################################


    @app.route('/api/movie-leaderboard', methods=['GET'])
    def get_song_leaderboard() -> Response:
        """
        Route to retrieve a leaderboard of movie sorted by play count.

        Returns:
            JSON response with a sorted leaderboard of movie.

        Raises:
            500 error if there is an issue generating the leaderboard.

        """
        try:
            app.logger.info("Received request to generate movie leaderboard")

            leaderboard_data = Movies.get_all_movie(sort_by_play_count=True)

            app.logger.info(f"Successfully generated movie leaderboard with {len(leaderboard_data)} entries")
            return make_response(jsonify({
                "status": "success",
                "leaderboard": leaderboard_data
            }), 200)

        except Exception as e:
            app.logger.error(f"Failed to generate movie leaderboard: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while generating the leaderboard",
                "details": str(e)
            }), 500)

    return app

if __name__ == '__main__':
    app = create_app()
    app.logger.info("Starting Flask app...")
    try:
        app.run(debug=True, host='0.0.0.0', port=5001)
    except Exception as e:
        app.logger.error(f"Flask app encountered an error: {e}")
    finally:
        app.logger.info("Flask app has stopped.")