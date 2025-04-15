from fastapi import APIRouter, HTTPException
import sqlite3
from typing import Optional

city_router_app = APIRouter()

DB_FILE = "data.db"


@city_router_app.get('/cities/')
async def getByCities(name: Optional[str] = None):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraint
    cursor = conn.cursor()
    try:
        if(name == None):
            cursor.execute("SELECT id,name FROM cities")

        else:
            cursor.execute("SELECT id,name FROM cities WHERE name like  ? COLLATE NOCASE", ('%' + name + '%',))
        
        return str(cursor.fetchall())
    except Exception as e:
        raise HTTPException(status_code = 404, detail=str(e))
    finally:
        conn.commit()
        conn.close()