# Movie Watchlist Application

A Flask-based web application for managing a personal movie watchlist. Users can create accounts, browse a movie catalog, and maintain their personal watchlist.

Images of test results are in the Test Results folder: 411-resources/HW/Project/watchlist/Test Results

## Features

- User authentication (signup, login, logout)
- Movie catalog management
- Personal watchlist functionality
- Secure password management
- RESTful API endpoints

## Project Structure

```
watchlist/
├── app.py              
├── config.py           
├── requirements.txt    
├── Dockerfile         
├── tests/            
│   ├── conftest.py
│   ├── test_api_utils.py
│   ├── test_movie_model.py
│   ├── test_user_model.py
│   └── test_watchlist_model.py
└── watchlist/         
    ├── models/        
    ├── utils/        
    └── db.py          


## Setup Instructions

1. **Using Virtual Environment**:
   ```bash
   ./setup_venv.sh
   ```

2. **Using Docker**:
   ```bash
   ./run_docker.sh
   ```

## API Documentation

### User Management

- `PUT /api/create-user`
  - Create a new user account
  - Required fields: username, password

- `POST /api/login`
  - Authenticate user
  - Required fields: username, password

- `POST /api/logout`
  - Logout current user
  - Requires authentication

- `POST /api/change-password`
  - Change user password
  - Required fields: new_password
  - Requires authentication

### Movie Catalog

- `POST /api/create-movie`
  - Add a new movie to catalog
  - Required fields: director, title, year, genre, duration
  - Requires authentication

- `GET /api/get-all-movie-from-catalog`
  - Retrieve all movies in catalog
  - Requires authentication

- `GET /api/get-movie-from-catalog-by-id/<movie_id>`
  - Get movie by ID
  - Requires authentication

- `GET /api/get-random-movie`
  - Get a random movie from catalog
  - Requires authentication

### Watchlist Management

- `POST /api/add-movie-to-watchlist`
  - Add movie to user's watchlist
  - Required fields: movie_id
  - Requires authentication

- `DELETE /api/remove-movie-from-watchlist`
  - Remove movie from watchlist
  - Required fields: movie_id
  - Requires authentication

- `POST /api/clear-watchlist`
  - Clear entire watchlist
  - Requires authentication

- `GET /api/get-all-movie-from-watchlist`
  - Get all movies in user's watchlist
  - Requires authentication


## Security Features

- Password hashing
- Session management
- Protected routes
- Input validation
- Error handling

## Dependencies

- Flask
- Flask-Login
- SQLAlchemy
- pytest
- python-dotenv

See `requirements.txt` for complete list of dependencies. 