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
    """Create a Flask application with the specified configuration."""
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
        app.logger.info("Health check endpoint hit")
        return make_response(jsonify({
            'status': 'success',
            'message': 'Service is running'
        }), 200)

    # --- User Management ---
    @app.route('/api/create-user', methods=['PUT'])
    def create_user() -> Response:
        try:
            data = request.get_json() or {}
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
        try:
            data = request.get_json() or {}
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
        logout_user()
        return make_response(jsonify({
            "status": "success",
            "message": "User logged out successfully"
        }), 200)

    @app.route('/api/change-password', methods=['POST'])
    @login_required
    def change_password() -> Response:
        try:
            data = request.get_json() or {}
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
        try:
            app.logger.info("Received request to recreate Users table")
            with app.app_context():
                Users.__table__.drop(db.engine)
                Users.__table__.create(db.engine)
            return make_response(jsonify({
                "status": "success",
                "message": "Users table recreated successfully"
            }), 200)
        except Exception as e:
            app.logger.error(f"Users table recreation failed: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while deleting users",
                "details": str(e)
            }), 500)

    # --- Movie Catalog ---
    @app.route('/api/reset-movies', methods=['DELETE'])
    def reset_movie() -> Response:
        try:
            app.logger.info("Received request to recreate Movies table")
            with app.app_context():
                Movies.__table__.drop(db.engine)
                Movies.__table__.create(db.engine)
            return make_response(jsonify({
                "status": "success",
                "message": "Movies table recreated successfully"
            }), 200)
        except Exception as e:
            app.logger.error(f"Movies table recreation failed: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while deleting movies",
                "details": str(e)
            }), 500)

    @app.route('/api/create-movie', methods=['POST'])
    @login_required
    def add_movie() -> Response:
        app.logger.info("Received request to add a new movie")
        try:
            data = request.get_json() or {}
            required = ["director", "title", "year", "genre", "duration"]
            missing = [f for f in required if f not in data]
            if missing:
                return make_response(jsonify({
                    "status": "error",
                    "message": f"Missing required fields: {', '.join(missing)}"
                }), 400)

            director = data["director"]
            title    = data["title"]
            year     = data["year"]
            genre    = data["genre"]
            duration = data["duration"]

            if (not isinstance(director, str) or not isinstance(title, str)
                or not isinstance(year, int) or not isinstance(genre, str)
                or not isinstance(duration, int)):
                return make_response(jsonify({
                    "status": "error",
                    "message": "Invalid input types: director/title/genre should be strings, year and duration should be integers"
                }), 400)

            Movies.create_movie(director=director, title=title, year=year,
                                genre=genre, duration=duration)
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

    @app.route('/api/delete-movie/<int:movie_id>', methods=['DELETE'])
    @login_required
    def delete_movie(movie_id: int) -> Response:
        try:
            app.logger.info(f"Received request to delete movie with ID {movie_id}")
            movie = Movies.get_movie_by_id(movie_id)
            if not movie:
                return make_response(jsonify({
                    "status": "error",
                    "message": f"Movie with ID {movie_id} not found"
                }), 400)
            Movies.delete_movie(movie_id)
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
        try:
            sort_by_play_count = request.args.get('sort_by_play_count', 'false').lower() == 'true'
            movies = Movies.get_all_movie(sort_by_play_count=sort_by_play_count)
            return make_response(jsonify({
                "status": "success",
                "movie":  movies
            }), 200)
        except Exception as e:
            app.logger.error(f"Failed to retrieve movies: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while retrieving movies",
                "details": str(e)
            }), 500)

    @app.route('/api/get-movie-from-catalog-by-id/<int:movie_id>', methods=['GET'])
    @login_required
    def get_movie_by_id(movie_id: int) -> Response:
        try:
            app.logger.info(f"Received request to retrieve movie with ID {movie_id}")
            movie = Movies.get_movie_by_id(movie_id)
            if not movie:
                return make_response(jsonify({
                    "status": "error",
                    "message": f"Movie with ID {movie_id} not found"
                }), 400)
            return make_response(jsonify({
                "status": "success",
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
        try:
            director = request.args.get('director')
            title    = request.args.get('title')
            year_str = request.args.get('year')
            if not director or not title or not year_str:
                return make_response(jsonify({
                    "status": "error",
                    "message": "Missing required query parameters: director, title, year"
                }), 400)
            try:
                year = int(year_str)
            except ValueError:
                return make_response(jsonify({
                    "status": "error",
                    "message": "Year must be an integer"
                }), 400)
            movie = Movies.get_movie_by_compound_key(director, title, year)
            return make_response(jsonify({
                "status": "success",
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
        try:
            movie = Movies.get_random_movie()
            return make_response(jsonify({
                "status": "success",
                "movie": movie
            }), 200)
        except Exception as e:
            app.logger.error(f"Failed to retrieve random movie: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while retrieving a random movie",
                "details": str(e)
            }), 500)

    # --- Watchlist Management ---

    @app.route('/api/add-movie-to-watchlist', methods=['POST'])
    @login_required
    def add_movie_to_watchlist() -> Response:
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
            title    = data["title"]
            try:
                year = int(data["year"])
            except ValueError:
                return make_response(jsonify({
                    "status": "error",
                    "message": "Year must be a valid integer"
                }), 400)
            movie = Movies.get_movie_by_compound_key(director, title, year)
            watchlist_model.add_movie_to_watchlist(movie.id)
            return make_response(jsonify({
                "status": "success",
                "message": f"Movie '{title}' by {director} ({year}) added to watchlist"
            }), 201)
        except ValueError as e:
            return make_response(jsonify({
                "status": "error",
                "message": str(e)
            }), 400)
        except Exception as e:
            app.logger.error(f"Failed to add movie to watchlist: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while adding the movie to the watchlist",
                "details": str(e)
            }), 500)

    @app.route('/api/remove-movie-from-watchlist', methods=['DELETE'])
    @login_required
    def remove_movie_from_watchlist() -> Response:
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
            title    = data["title"]
            try:
                year = int(data["year"])
            except ValueError:
                return make_response(jsonify({
                    "status": "error",
                    "message": "Year must be a valid integer"
                }), 400)
            movie = Movies.get_movie_by_compound_key(director, title, year)
            watchlist_model.remove_movie_by_movie_id(movie.id)
            return make_response(jsonify({
                "status": "success",
                "message": f"Movie '{title}' by {director} ({year}) removed from watchlist"
            }), 200)
        except ValueError as e:
            return make_response(jsonify({
                "status": "error",
                "message": str(e)
            }), 400)
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
        try:
            watchlist_model.remove_movie_by_movie_number(movie_number)
            return make_response(jsonify({
                "status": "success",
                "message": f"Movie at movie number {movie_number} removed from watchlist"
            }), 200)
        except ValueError as e:
            return make_response(jsonify({
                "status": "error",
                "message": str(e)
            }), 404)
        except Exception as e:
            app.logger.error(f"Failed to remove movie by number: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal error occurred while removing the movie from the watchlist",
                "details": str(e)
            }), 500)

    @app.route('/api/clear-watchlist', methods=['POST'])
    @login_required
    def clear_watchlist() -> Response:
        try:
            watchlist_model.clear_watchlist()
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

    # --- PLAYBACK / STATS omitted for brevity ---

    # <<< HERE is the restored endpoint >>>
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
