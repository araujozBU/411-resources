import requests


def run_smoketest():
    base_url = "http://localhost:5001/api"
    username = "test"
    password = "test"

    # Sample movies for creation
    movie_beatles = {
        "director": "The Beatles",
        "title":    "Come Together",
        "year":     1969,
        "genre":    "Rock",
        "duration": 259
    }

    movie_nirvana = {
        "director": "Nirvana",
        "title":    "Smells Like Teen Spirit",
        "year":     1991,
        "genre":    "Grunge",
        "duration": 301
    }

    # 1) Health check
    health = requests.get(f"{base_url}/health")
    assert health.status_code == 200
    assert health.json()["status"] == "success"
    print("Health check successful")

    # 2) Reset tables
    r = requests.delete(f"{base_url}/reset-users")
    assert r.status_code == 200 and r.json()["status"] == "success"
    print("Reset users successful")

    r = requests.delete(f"{base_url}/reset-movies")
    assert r.status_code == 200 and r.json()["status"] == "success"
    print("Reset movies successful")

    # 3) Create user
    r = requests.put(f"{base_url}/create-user", json={"username": username, "password": password})
    assert r.status_code == 201 and r.json()["status"] == "success"
    print("User creation successful")

    session = requests.Session()

    # 4) Log in
    r = session.post(f"{base_url}/login", json={"username": username, "password": password})
    assert r.status_code == 200 and r.json()["status"] == "success"
    print("Login successful")

    # 5) Create first movie
    r = session.post(f"{base_url}/create-movie", json=movie_beatles)
    assert r.status_code == 201 and r.json()["status"] == "success"
    print("First movie creation successful")

    # 6) Change password
    r = session.post(f"{base_url}/change-password", json={"new_password": "newpass"})
    assert r.status_code == 200 and r.json()["status"] == "success"
    print("Password change successful")

    # 7) Re‑login with new password
    session = requests.Session()
    r = session.post(f"{base_url}/login", json={"username": username, "password": "newpass"})
    assert r.status_code == 200 and r.json()["status"] == "success"
    print("Login with new password successful")

    # 8) Create second movie
    r = session.post(f"{base_url}/create-movie", json=movie_nirvana)
    assert r.status_code == 201 and r.json()["status"] == "success"
    print("Second movie creation successful")

    # 9) Clear watchlist (in‑memory)
    r = session.post(f"{base_url}/clear-watchlist")
    assert r.status_code == 200 and r.json()["status"] == "success"
    print("Cleared watchlist successful")

    # 10) Add first movie to watchlist
    r = session.post(
        f"{base_url}/add-movie-to-watchlist",
        json={
            "director": movie_beatles["director"],
            "title":    movie_beatles["title"],
            "year":     movie_beatles["year"],
        }
    )
    assert r.status_code == 201 and r.json()["status"] == "success"
    print("Add to watchlist successful")

    # 11) Get watchlist
    r = session.get(f"{base_url}/get-all-movie-from-watchlist")
    assert r.status_code == 200 and r.json()["status"] == "success"
    print("Get watchlist successful")

    # 12) Logout
    r = session.post(f"{base_url}/logout")
    assert r.status_code == 200 and r.json()["status"] == "success"
    print("Logout successful")

    # 13) Ensure protected routes now fail
    r = session.post(f"{base_url}/create-movie", json=movie_nirvana)
    assert r.status_code == 401 and r.json()["status"] == "error"
    print("Create-movie failed as expected when logged out")


if __name__ == "__main__":
    run_smoketest()
