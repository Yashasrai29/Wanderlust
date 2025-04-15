from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sqlite3
from typing import List
import math

places_app = APIRouter()

DB_FILE = 'data.db'

ROAD_DISTANCE_CONSTANT = 1.35

# Haversine formula to calculate distance between two lat/lon points
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of Earth in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance * ROAD_DISTANCE_CONSTANT # Converting airial distance into land(road) distance

class PlaceResponse(BaseModel):
    name: str
    latitude: float
    longitude: float
    distance: float

@places_app.get("/cities/nearest/", response_model=List[PlaceResponse])
async def get_nearest_cities(lat: float, lon: float, city_id : str):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT name, latitude, longitude FROM places where city_id = ?", (city_id,))
        places = cursor.fetchall()

        if not places:
            raise HTTPException(status_code=404, detail="No places found.")
        
        places_with_distance = []
        for name, latitude, longitude in places:
            distance = haversine(lat, lon, latitude, longitude)
            places_with_distance.append({
                "name": name,
                "latitude": latitude,
                "longitude": longitude,
                "distance": distance
            })

        places_with_distance.sort(key=lambda x: x["distance"])

        return places_with_distance

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        conn.close()
        
@places_app.get('/distance')
async def get_distance_btw_two(lat1: float, long1: float, lat2: float, long2: float):
    return haversine(lat1, long1, lat2, long2)