from fastapi import APIRouter, File, UploadFile, HTTPException
import pandas as pd
import sqlite3
import io
import json

master_data_app = APIRouter()

DB_FILE = "data.db"

@master_data_app.post("/upload_cities/")
async def upload_cities_excel(file: UploadFile = File(...)):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Please upload a valid Excel file.")

    content = await file.read()
    try:
        city = "city"
        df = pd.read_excel(io.BytesIO(content), sheet_name=city)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Sheet city not found. {str(e)}")

    
    df.columns = df.columns.str.strip()

    expected_columns = ["id", "name", "latitude", "longitude"]
    if list(df.columns) != expected_columns:
        raise HTTPException(
            status_code=400,
            detail=f"Expected columns: {expected_columns}, but got: {list(df.columns)}"
    )
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Enable foreign key support
    cursor.execute("PRAGMA foreign_keys = ON")

    # Create the 'cities' table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cities (
            id TEXT PRIMARY KEY,
            name TEXT,
            latitude DOUBLE,
            longitude DOUBLE
        )
    """)

    # Insert each row
    for _, row in df.iterrows():
        try:
            print(row["id"], row["name"].strip(), row["latitude"], row["longitude"])
            cursor.execute("""
                INSERT OR REPLACE INTO cities (id, name, latitude, longitude)
                VALUES (?, ?, ?, ?)
            """, (row["id"], row["name"].strip(), row["latitude"], row["longitude"]))
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Error inserting row: {row.to_dict()} - {str(e)}")
    
    conn.commit()
    conn.close()


@master_data_app.post("/upload_places/")
async def upload_places_excel(file: UploadFile = File(...)):
    if not file.filename.endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an Excel file.")

    content = await file.read()
    name = "places"
    df = pd.read_excel(io.BytesIO(content), sheet_name = name)
    print(df.to_string(index=False))
    
    expected_columns = ['id', 'city_id', 'name', 'tags', 'latitude', 'longitude', 'tf', 'visit_duration']
    if list(df.columns) != expected_columns:
        raise HTTPException(status_code=400, detail=f"Excel columns must match: {expected_columns}")

    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraint
    cursor = conn.cursor()

    # Create 'cities' table (foreign key target)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cities (
            id INTEGER PRIMARY KEY,
            name TEXT
        )
    ''')

    # Create 'places' table with foreign key on city_id
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS places (
            id TEXT PRIMARY KEY,
            city_id TEXT,
            name TEXT,
            tags TEXT,
            latitude DOUBLE,
            longitude DOUBLE,
            tf DOUBLE,
            visit_duration DOUBLE,
            FOREIGN KEY(city_id) REFERENCES cities(id) ON DELETE CASCADE
        )
    ''')

    # Insert data into 'places' table
    for _, row in df.iterrows():
        # Check if city_id exists in 'cities' table
        cursor.execute("SELECT id FROM cities WHERE id = ?", (row['city_id'],))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=400, detail=f"City ID {row['city_id']} not found in cities table.")

        tags_str = row["tags"]
        tags_list = [tag.strip() for tag in tags_str.split(",")]
        tags_json = json.dumps(tags_list)
        cursor.execute('''
            INSERT OR REPLACE INTO places (id, city_id, name, tags, latitude, longitude, tf, visit_duration)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (row["id"], row["city_id"], row["name"], tags_json, row["latitude"], row["longitude"], row["tf"], row["visit_duration"]))

    conn.commit()
    conn.close()

    return {"message": f"Inserted {len(df)} rows into 'places' table with foreign key checks."}
