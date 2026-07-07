import os
import jwt
import requests
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from passlib.context import CryptContext
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Configure application
app = FastAPI()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
load_dotenv()

# Get credentials from .env file
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_name = os.getenv("DB_NAME")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

# Engine will allow to CRUD info to and from the MySQL database with SQLAlchemy instead of mysql.connector
engine = create_engine(f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}")

# JWT Creation
def create_jwt_token(user_id: int):
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

# JWT Validation
def verify_jwt_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        return user_id
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    
# JWT Verification (for access in restricted areas)
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user_id = verify_jwt_token(token)

    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token.")
    
    return user_id

# classes/Pydantic Models to use in the routes
class UserAuth(BaseModel):
    username: str = Field(min_length=4, max_length=15)
    password: str = Field(min_length=12, max_length=60)

class City(BaseModel):
    name: str = Field(max_length=50)
    latitude: float = Field(ge=-90, le=90) # Latitude (between -90° and 90°)
    longitude: float = Field(ge=-180, le=180) # Longitude (between -180° and 180°)

class CityResponse(BaseModel):
    id: int
    user_id: int
    name: str = Field(max_length=50)
    latitude: float = Field(ge=-90, le=90) # Latitude (between -90° and 90°)
    longitude: float = Field(ge=-180, le=180) # Longitude (between -180° and 180°)
    created_at: datetime

# Function for Open-Meteo API climate searching (base url is expanded by params used later)
def build_weather_url(lat: float, lon: float):
    base_url = "https://api.open-meteo.com/v1/forecast"
    params = f"?latitude={lat}&longitude={lon}"
    params += "&current=temperature_2m,wind_speed_10m"
    params += "&hourly=temperature_2m"
    params += "&daily=temperature_2m_max,temperature_2m_min"
    params += "&timezone=auto"
    return base_url + params

# Response dictionaries for Swagger documentation (accessible at localhost:8000/docs)
register_responses = {
    200: {
        "description": "User registered successfully",
        "content": {
            "application/json": {
                "example": {
                    "id": 1,
                    "message": "User created successfully."
                }
            }
        }
    },
    400: {
        "description": "Username already exists"
    }
}

login_responses = {
    200: {
        "description": "Login successful, returns JWT token",
        "content": {
            "application/json": {
                "example": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer"
                }
            }
        }
    },
    401: {
        "description": "Invalid credentials (user not found or wrong password)"
    }
}

add_city_responses = {
    200: {
        "description": "City added successfully",
        "content": {
            "application/json": {
                "example": {
                    "id": 1,
                    "user_id": 1,
                    "name": "São Paulo",
                    "latitude": -23.5505,
                    "longitude": -46.6333,
                    "created_at": "2026-07-06T22:25:28"
                }
            }
        }
    },
    401: {
        "description": "Invalid or missing token"
    },
    422: {
        "description": "Validation error - invalid latitude/longitude or missing fields"
    }
}

get_cities_responses = {
    200: {
        "description": "List of all cities saved by the user",
        "content": {
            "application/json": {
                "example": [
                    {
                        "id": 1,
                        "user_id": 1,
                        "name": "São Paulo",
                        "latitude": -23.5505,
                        "longitude": -46.6333,
                        "created_at": "2026-07-06T22:25:28"
                    }
                ]
            }
        }
    },
    401: {
        "description": "Invalid or missing token"
    }
}

get_weather_responses = {
    200: {
        "description": "Current weather data for the city",
        "content": {
            "application/json": {
                "example": {
                    "city_name": "São Paulo",
                    "latitude": -23.5505,
                    "longitude": -46.6333,
                    "current_temp": 25.5,
                    "current_wind": 10.2,
                    "today_max": 28.0,
                    "today_min": 20.5,
                    "snapshot_time": "Last updated: 2026-07-07T15:30"
                }
            }
        }
    },
    401: {
        "description": "Invalid or missing token"
    },
    403: {
        "description": "City belongs to another user"
    },
    404: {
        "description": "City not found"
    }
}

delete_city_responses = {
    200: {
        "description": "City deleted successfully",
        "content": {
            "application/json": {
                "example": {
                    "message": "City has been successfully deleted."
                }
            }
        }
    },
    401: {
        "description": "Invalid or missing token"
    },
    404: {
        "description": "City not found or doesn't belong to user"
    }
}

@app.post("/register",
          summary="Register a new user",
          description="Create a new user account with username and password",
          responses=register_responses)
def register(user: UserAuth):
    # Get user inputs (request info)
    username = user.username
    password = user.password

    # Hash password before inserting into the database
    hashed_pass = pwd_context.hash(password)

    # Connect to database
    with engine.connect() as conn:
        query = conn.execute(text("SELECT * FROM users WHERE username = :username"), {"username": username})
        existing_user = query.fetchone()

        # If username already exists, return error 400
        if existing_user is not None:
            raise HTTPException(status_code=400, detail="Username already exists. Try Again.")
        
        # If it doesn't exist, add the new user into the database
        conn.execute(text("INSERT INTO users (username, password) VALUES (:username, :password)"), {"username": username, "password": hashed_pass})
        conn.commit()

        # Get id from the recently added user
        query = conn.execute(text("SELECT * FROM users WHERE id = LAST_INSERT_ID()"))
        results = query.fetchone()

        # Convert row to dict
        results_dict = dict(results._mapping)

        # Reorganize the new dict with user_id, and return it
        new_dict = {
            "id": results_dict["id"],
            "message": "User created successfully."
        }
        return new_dict
    
@app.post("/login",
          summary="Allows a user to log in",
          description="Logs user into the application and gives him a JWT",
          responses=login_responses)
def login(user: UserAuth):
    # Get user inputs (request info)
    username = user.username
    password = user.password

    # Connect to database
    with engine.connect() as conn:
        # Check if username is registered
        query = conn.execute(text("SELECT * FROM users WHERE username = :username"), {"username": username})
        existing_user = query.fetchone()

        # If not, return 401
        if not existing_user:
            raise HTTPException(status_code=401, detail="User not found or doesn't exist.")
        
        # Convert from row to dict
        cur_user = dict(existing_user._mapping)

        # Check if the password inputted is the same as the one saved in the database
        pass_check = pwd_context.verify(password, cur_user['password'])
        if not pass_check: # If the check comes as false
            raise HTTPException(status_code=401, detail="Wrong password. Try Again.")
        
        # If username and password are correct, then create a JWT token
        token = create_jwt_token(cur_user['id'])

        # Return token to user to allow access
        return {"access_token": token, "token_type": "bearer"}
    
@app.post("/cities",
          summary="Allows the user to register a city",
          description="Allows the user to add a city to the database",
          responses=add_city_responses)
def add_city(city: City, user_id: int = Depends(verify_token)):
    # Get inputs (request info)
    name = city.name
    latitude = city.latitude
    longitude = city.longitude

    # Connect to database
    with engine.connect() as conn:
        # INSERT city info and commit
        conn.execute(text("INSERT INTO cities (user_id, name, latitude, longitude) VALUES (:user_id, :name, :latitude, :longitude)"),
                     {"user_id": user_id, "name":name, "latitude": latitude, "longitude": longitude})
        conn.commit()

        # Get id from the recently added city
        query = conn.execute(text("SELECT * FROM cities WHERE id = LAST_INSERT_ID()"))
        results = query.fetchone()

        # Convert row to dict
        results_dict = dict(results._mapping)

        # Reorganize the new dict with all info from recently added city, and return it
        city_dict = {
            "id": results_dict["id"],
            "user_id": results_dict["user_id"],
            "name": results_dict["name"],
            "latitude": results_dict["latitude"],
            "longitude": results_dict["longitude"],
            "created_at": results_dict["created_at"]
        }
        response = CityResponse(**city_dict) # Add data/info to the Pydantic model
        # Return the Pydantic model with all data/info
        return response
    
@app.get("/cities",
         summary="Returns a list of all cities registered by a user",
         description="Returns a list of all cities registered by a user in the database",
         responses=get_cities_responses)
def get_city(user_id: int = Depends(verify_token)):
    # Connect to database
    with engine.connect() as conn:
        # Get all cities the user has registered
        query = conn.execute(text("SELECT * FROM cities WHERE user_id = :user_id"), {"user_id": user_id})
        results = query.fetchall()

        # Create a empty list to store all cities registered
        registered_cities = []

        # For each registered city
        for city_row in results:
            # Convert them from row to dict
            results_dict = dict(city_row._mapping)

            # Put all city data/info into a new dict
            city_dict = {
                "id": results_dict["id"],
                "user_id": results_dict["user_id"],
                "name": results_dict["name"],
                "latitude": results_dict["latitude"],
                "longitude": results_dict["longitude"],
                "created_at": results_dict["created_at"]
            }
            # Add the city data dict to the city Pydantic Model
            registered_cities.append(CityResponse(**city_dict))
        
        # Return a registered cities list registered by the user
        return registered_cities
    
@app.get("/cities/{city_id}/weather",
         summary="Show the current weather data of the selected city",
         description="Returns a list of current weather data about the city of id 'city_id' ",
         responses=get_weather_responses)
def get_city_weather(city_id: int, user_id: int = Depends(verify_token)):
    # Connect to database
    with engine.connect() as conn:
        # Check if the city exists in the database
        query = conn.execute(text("SELECT * FROM cities WHERE id = :id"), {"id": city_id})
        results = query.fetchone()

        # Check if the city exists
        if results is None:
            raise HTTPException(status_code=404, detail="City not found or doesn't exist.")

        # Convert existing_city from row to dict
        existing_city = dict(results._mapping)
        
        # Check if the existing city was registered by current logged in user (converted to dict to make comparison)
        if existing_city['user_id'] != user_id:
            raise HTTPException(status_code=403, detail="Access forbidden. You aren't allowed to view this information.")
        
        # If it exists and it was registered by the current logged user, build Open-Meteo url to make a request
        om_url = build_weather_url(existing_city['latitude'], existing_city['longitude'])

        # Make the request to Open-Meteo API
        weather_request = requests.get(om_url)

        # Check if the request was successful
        if weather_request.status_code == 200:
            # Convert json to dict
            weather_data = weather_request.json()

            # Get all important data/info from the city weather_data, SQL query (existing_city)
            city_weather_data = {
                # Basic city info
                "city_name": existing_city["name"],
                "latitude": existing_city["latitude"],
                "longitude": existing_city["longitude"],
                # Current Weather
                "current_temp": weather_data["current"]["temperature_2m"],
                "current_wind": weather_data["current"]["wind_speed_10m"],
                # Today's highest and lowest temperature
                "today_max": weather_data["daily"]["temperature_2m_max"][0],
                "today_min": weather_data["daily"]["temperature_2m_min"][0],
                # Time weather snapshot was taken
                "snapshot_time": f"Last updated: {weather_data['current']['time']}"
            }
            # Return city weather data to user
            return city_weather_data
        else:
            # If an error occurs, show error message
            return {"message": "An error occurred with the request. Please try again or review the documentation."}
        
@app.delete("/cities/{city_id}",
            summary="Deletes a user-registered city",
            description="Allows the user to delete a registered city from the database",
            responses=delete_city_responses)
def delete_city(city_id: int, user_id: int = Depends(verify_token)):
    # Connect to database
    with engine.connect() as conn:
        # Search for the city of id "city_id"
        query = conn.execute(text("SELECT * FROM cities WHERE id = :id AND user_id = :user_id"), {"id": city_id, "user_id": user_id})
        results = query.fetchone()

        # Check if the city searched exists
        if results is None:
            raise HTTPException(status_code=404, detail="City not found or doesn't exist.")
        
        # If all valid, delete the city from the database
        conn.execute(text("DELETE FROM cities WHERE id = :id AND user_id = :user_id"), {"id": city_id, "user_id": user_id})
        conn.commit()

        # Return a success message to the user
        return {"message": "City has been successfully deleted."}