# Weather API 🌤️

A RESTful API for tracking weather data of your favorite cities, built with FastAPI and powered by [Open-Meteo](https://github.com/open-meteo/open-meteo).

---

## About

Weather API is a backend application that allows authenticated users to save cities and retrieve real-time weather data for each one. Built as a learning project to practice FastAPI, JWT authentication, SQLAlchemy Core, and third-party API integration.

---

## Features

- User registration and login with hashed passwords (Argon2)
- JWT-based authentication for protected routes
- Save, list, and delete favorite cities
- Real-time weather data fetched from [Open-Meteo](https://github.com/open-meteo/open-meteo) (no API key required)
- Automatic API documentation via Swagger UI (`/docs`) and ReDoc (`/redoc`)
- Input validation with Pydantic models

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI |
| Database | MySQL |
| ORM/Query | SQLAlchemy Core + `text()` |
| Validation | Pydantic v2 |
| Authentication | PyJWT (HS256) |
| Password Hashing | Passlib + Argon2 |
| External API | Open-Meteo |
| HTTP Client | Requests |
| Server | Uvicorn (ASGI) |
| Environment | python-dotenv |

---

## Project Structure

```
Weather-API/
├── main.py          # All routes, models, and application logic
├── schema.sql       # Versioned database schema
├── .env             # Environment variables (not committed)
├── .gitignore
└── README.md
```

---

## Database Schema

```sql
-- Users table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(15) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cities table
CREATE TABLE cities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(50) NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

> **Note:** The `cities` table uses `ON DELETE CASCADE` on the `user_id` foreign key. This means that if a user is deleted from the `users` table, all cities associated with that user will be automatically deleted from the `cities` table as well.

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- MySQL (via XAMPP, WAMP, or standalone)
- phpMyAdmin (optional, for database management)

### Steps

**1. Clone the repository:**
```bash
git clone https://github.com/Yahg0h/weather-api.git
cd weather-api
```

**2. Create and activate a virtual environment:**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

**3. Install dependencies:**
```bash
pip install fastapi uvicorn sqlalchemy pymysql pydantic passlib argon2-cffi PyJWT python-dotenv requests
```

**4. Create the database:**

Open phpMyAdmin (or your MySQL client), create a new database, and run the contents of `schema.sql`.

**5. Configure environment variables:**

Create a `.env` file in the root directory:
```
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_NAME=your_database_name
SECRET_KEY=your_secret_key_here
```

To generate a secure `SECRET_KEY`, run:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**6. Run the server:**
```bash
python -m uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.
Swagger docs available at `http://localhost:8000/docs`.

---

## Routes

### Authentication

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| POST | `/register` | No | Register a new user |
| POST | `/login` | No | Login and receive a JWT token |

### Cities

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| POST | `/cities` | Yes | Add a city to your list |
| GET | `/cities` | Yes | List all your saved cities |
| GET | `/cities/{city_id}/weather` | Yes | Get real-time weather for a city |
| DELETE | `/cities/{city_id}` | Yes | Remove a city from your list |

### Authentication Header

For protected routes, include the JWT token in the request header:
```
Authorization: Bearer <your_token_here>
```

---

## Security

- Passwords are hashed using **Argon2** before being stored in the database. Plain-text passwords are never saved.
- Authentication is handled via **JWT tokens** (HS256 algorithm) with a 1-hour expiration.
- The `SECRET_KEY` used to sign tokens is stored in `.env` and never committed to version control.
- Parameterized queries via SQLAlchemy `text()` prevent SQL injection.
- City ownership is validated on every request — users can only view or delete their own cities.

---

## Troubleshooting

### `uvicorn` is not recognized as a command
Instead of running the command with:
```bash
uvicorn main:app --reload
````
Run it using the Python module flag, as previously recommended:
```bash
python -m uvicorn main:app --reload
```

### `ValueError: password cannot be longer than 72 bytes`
This occurs when using bcrypt for password hashing—instead of Argon2—with passwords exceeding 72 characters. Switch to Argon2 (the default and recommended option) or limit `max_length` to 60 in your Pydantic model.

### `InsecureKeyLengthWarning` for JWT
Your `SECRET_KEY` is too short. Generate a secure key with at least 32 bytes, as previously recommended, with:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### `sqlalchemy.exc.OperationalError: Access denied for user`
Your `.env` credentials don't match your MySQL user. Check:
- `DB_USER` and `DB_PASSWORD` match what's configured in phpMyAdmin (or your MySQL client)
- The MySQL server is running
- The database name in `DB_NAME` exists

### `401 Unauthorized` after changing `SECRET_KEY`
Tokens signed with the old key are invalid after a key change. Log in again to get a new token.

### `KeyError: 'hourly'` on weather route
The Open-Meteo URL is missing the `hourly` parameter. Make sure `build_weather_url()` includes all required parameters:
```python
params += "&hourly=temperature_2m"
```

### `LocationParseError` on Open-Meteo request
The URL is malformed. Construct the URL in parts instead of using a single f-string, as is done in the original standard code.:
```python
base_url = "https://api.open-meteo.com/v1/forecast"
params = f"?latitude={lat}&longitude={lon}"
params += "&current=temperature_2m,wind_speed_10m"
```
>For more information about the Open-Meteo URL and how to construct it correctly, consult the API documentation [here](https://open-meteo.com/en/docs).
---

## License

This project is licensed under the MIT License - free to use and modfiy. See LICENSE file for more details.

---

## Special Thanks

**Open-Meteo** (Open-Meteo Weather API)
- GitHub Repository: [open-meteo](https://github.com/open-meteo/open-meteo)
- Website: [open-meteo.com](https://open-meteo.com/)
- Documentation: [open-meteo.com/en/docs](https://open-meteo.com/en/docs)

---

## Author

Made by **Yahgoh**. I hope you like it!
- GitHub: [@Yahg0h](https://github.com/Yahg0h)
