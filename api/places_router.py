from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sqlite3
from typing import List
import math

places_app = APIRouter()

DB_FILE = 'data.db'

ROAD_DISTANCE_CONSTANT = 1.35

IDEAL_TRAVEL_SPEED = 60

HOUR = 60

TRAVELLING_HOURS = 12

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
    total: float
    next_place_distance: float
    next_place: str
    time_required_mintues: float
    time_required_hours: float
    tf: float
    visit_duration: float

# @places_app.get("/cities/places/", response_model=List[PlaceResponse])
@places_app.get("/cities/places/")
async def get_nearest_cities(lat: float, lon: float, city_id : str):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT name, latitude, longitude, tf, visit_duration FROM places where city_id = ?", (city_id,))
        places = cursor.fetchall()

        if not places:
            raise HTTPException(status_code=404, detail="No places found.")
        
        places_with_distance = []
        for name, latitude, longitude, tf, visit_duration in places:
            distance = haversine(lat, lon, latitude, longitude)
            places_with_distance.append({
                "name": name,
                "latitude": latitude,
                "longitude": longitude,
                "total": distance,
                "next_place_distance" :0.0,
                "next_place" : "",
                "time_required_mintues": 0.0,
                "time_required_hours": 0.0,
                "tf" : tf,
                "visit_duration" : visit_duration
            })
            
        places_with_distance.sort(key=lambda x: x["total"])
        total_time = 0.0

        
        for index in range(0, len(places_with_distance) - 1):
            first = places_with_distance[index]
            second = places_with_distance[index+1]
            first["next_place_distance"] = haversine(first["latitude"], first["longitude"], second["latitude"], second["longitude"])
            first["next_place"] = second["name"]
            first["time_required_mintues"] = ((first["next_place_distance"] / IDEAL_TRAVEL_SPEED )  /  ( (first["tf"] + second["tf"]) / 2 ) ) * HOUR
            first["time_required_hours"] = first["time_required_mintues"] / 60
            places_with_distance[index] = first
            total_time += first["visit_duration"] + first["time_required_hours"]

        first = places_with_distance[0]
        last = places_with_distance[len(places_with_distance) -1]
       
        arrival_time = haversine(lat, lon, first["latitude"], first["longitude"]) / IDEAL_TRAVEL_SPEED;
        
        departure_time = haversine(last["latitude"], last["longitude"], lat, lon) / IDEAL_TRAVEL_SPEED;
        
        total_time += (arrival_time + departure_time)
        
        days = total_time / 12
        nights = days -1
        
        return {
                "itinerary" : {
                    "arrival_time_from_source_to_destination" : round(arrival_time, 2),
                    "departure_time_from_destination_to_source" : round(departure_time, 2),
                    "days" : round(days),
                    "nights" : round(nights)
                },
                "places_details" : places_with_distance
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        conn.close()
        
@places_app.get('/distance')
async def get_distance_btw_two(lat1: float, long1: float, lat2: float, long2: float):
    return haversine(lat1, long1, lat2, long2)