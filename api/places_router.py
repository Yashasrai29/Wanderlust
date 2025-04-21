from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sqlite3
from typing import List, Optional
import math
import os
import openai  # Ensure you have installed the openai package

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
    return distance * ROAD_DISTANCE_CONSTANT  # Converting aerial distance into road (land) distance

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

@places_app.post("/users/cities/places/")
async def get_itinerary(source_id: str, city_id: str, tags: Optional[List[str]] = None):
    # Connect to the SQLite DB and fetch details based on city_id (and tags if provided)
    
   
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT latitude, longitude FROM places WHERE city_id = ? LIMIT 1", (source_id,))
        city = cursor.fetchone()
        if city is None:
            raise HTTPException(status_code=404, detail="Source city not found.")
        lat, lon = city  # Unpack tuple instead of using string keys

        # Build query with optional tag filtering
        if tags is not None:
            query = "SELECT name, latitude, longitude, tf, visit_duration FROM places WHERE city_id = ?"
            params = [city_id]
            for tag in tags:
                query += " AND tags LIKE ?"
                params.append(f"%{tag}%")
            cursor.execute(query, params)
        else:
            cursor.execute("SELECT name, latitude, longitude, tf, visit_duration FROM places WHERE city_id = ?", (city_id,))
        
        places = cursor.fetchall()
        if not places:
            raise HTTPException(status_code=404, detail="No places found.")
        
        # Process and calculate itinerary details
        places_with_distance = []
        for name, latitude, longitude, tf, visit_duration in places:
            distance = haversine(lat, lon, latitude, longitude)
            places_with_distance.append({
                "name": name,
                "latitude": latitude,
                "longitude": longitude,
                "total": distance,
                "next_place_distance": 0.0,
                "next_place": "",
                "time_required_mintues": 0.0,
                "time_required_hours": 0.0,
                "tf": tf,
                "visit_duration": visit_duration
            })
        
        # Sort places by distance from source
        places_with_distance.sort(key=lambda x: x["total"])
        total_time = 0.0

        # Calculate travel times and update itinerary info between consecutive places
        for index in range(len(places_with_distance) - 1):
            first = places_with_distance[index]
            second = places_with_distance[index + 1]
            first["next_place_distance"] = haversine(first["latitude"], first["longitude"], second["latitude"], second["longitude"])
            first["next_place"] = second["name"]
            first["time_required_mintues"] = ((first["next_place_distance"] / IDEAL_TRAVEL_SPEED) / ((first["tf"] + second["tf"]) / 2)) * HOUR
            first["time_required_hours"] = first["time_required_mintues"] / 60
            total_time += first["visit_duration"] + first["time_required_hours"]

        first_place = places_with_distance[0]
        last_place = places_with_distance[-1]
        
        # Calculate arrival and departure times
        arrival_time = haversine(lat, lon, first_place["latitude"], first_place["longitude"]) / IDEAL_TRAVEL_SPEED
        departure_time = haversine(last_place["latitude"], last_place["longitude"], lat, lon) / IDEAL_TRAVEL_SPEED
        total_time += (arrival_time + departure_time)
        
        days = total_time / TRAVELLING_HOURS
        nights = days - 1
        
        # Build the result JSON
        result_json = {
            "itinerary": {
                "arrival_time_from_source_to_destination": round(arrival_time, 2),
                "departure_time_from_destination_to_source": round(departure_time, 2),
                "days": round(days),
                "nights": round(nights)
            },
            "places_details": places_with_distance
        }
        
        # ---------- Azure OpenAI Integration Start ----------
        # Set up Azure OpenAI with your credentials
        endpoint = "https://openaitesttc.openai.azure.com/"
        deployment = "gpt-4o"  # Your deployment name
        api_key = "2AlTledfY3v1QFfE0kFrlSnq2WiwRbYCkiWJMjteDTUlknwuUKrOJQQJ99BDAC5T7U2XJ3w3AAABACOGPBUU"  # Replace with your actual API key
        api_version = "2024-12-01-preview"

        openai.api_type = "azure"
        openai.api_base = endpoint
        openai.api_key = api_key
        openai.api_version = api_version
        
        prompt = (
            "You are a travel assistant who explains travel plans in a clear, structured, day-by-day format. "
            "You should also provide a short (2–3 sentence) descriptive summary for each place mentioned.\n\n"
            "1) At the top, state:\n"
            "   [Arrival time from the starting location]: (hours and minutes)\n"
            "   [Departure time back to the starting location]: (hours and minutes)\n"
            "   [Total number of days]:\n"
            "   [Total number of nights]:\n"
            "   [Total number of places to visit]:\n\n" 
            "2) For each day, produce a section in this style:\n"
            "[Day X:\n"
            "   1. Visit <Place Name> (Description: <A 2–3 sentence summary of this place>)\n"
            "      (visit duration: H hr M min).\n"
            "      Next Location: <Next Place>\n"
            "      Travel to <Next Place>: (D km away); (travel time: H hr M min).\n\n"
            "   2. Visit <Next Place> (Description: <…>)\n"
            "      (visit duration: …).\n"
            "      Next Location: <Next Next Place>\n"
            "      Travel to <Next Next Place>: (… km away); (travel time: …).\n"
            "]\n\n"
            "Ensure proper indentation for readability. Leave a blank line between each place entry. "
            "Continue numbering days and stops in the same bracketed, numeric-list style. "
            "Do not use any other bullets or asterisks except the single '(Description:' line for each place.\n\n"
            "Now convert the following JSON data into that format:\n"
            f"{result_json}"
        )


        # Use the ChatCompletion interface (with the new parameter: deployment_id)
        # response = await openai.ChatCompletion.create(
        response =  openai.ChatCompletion.create(
            deployment_id=deployment,
            messages=[
                {"role": "system", "content": "You are a travel assistant who explains travel itineraries in simple, friendly language."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7,
            top_p=1.0,
        )

        natural_summary = response.choices[0].message.content.strip()
        
        
        # ---------- Azure OpenAI Integration End ----------

        # Optionally, write the summary to a text file (this will be stored in your project directory)
        with open("summary.txt", "w") as f:
            f.write(natural_summary)

        # Print the summary to command-line
        print("Natural Language Summary:\n", natural_summary)

        # Return the LLM-generated natural language summary in the API response
        return {"summary": natural_summary}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        conn.close()
        
@places_app.get('/distance')
async def get_distance_btw_two(lat1: float, long1: float, lat2: float, long2: float):
    return {"distance": haversine(lat1, long1, lat2, long2)}
