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

#JWT Creation
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

# Function for Open-Meteo API climate searching
def build_weather_url(lat: float, lon: float):
    return f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"

@app.post("/register")
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
    
@app.post("/login")
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
    
@app.post("/cities")
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
    
@app.get("/cities")
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

            