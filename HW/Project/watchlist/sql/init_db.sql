DROP TABLE IF EXISTS Movies;
CREATE TABLE Movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    director TEXT NOT NULL,
    title TEXT NOT NULL,
    year INTEGER NOT NULL CHECK(year >= 1900),
    genre TEXT NOT NULL,
    duration INTEGER NOT NULL CHECK(duration > 0),
    play_count INTEGER DEFAULT 0,
    UNIQUE(director, title, year)
);

CREATE INDEX idx_movies_director_title ON Movies(director, title);
CREATE INDEX idx_movies_year ON Movies(year);
CREATE INDEX idx_movies_play_count ON Movies(play_count);