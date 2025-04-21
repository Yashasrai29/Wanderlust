from fastapi import FastAPI, File, UploadFile, HTTPException
import pandas as pd
import sqlite3
import io
import json
from api.master_data_router import master_data_app
from api.city_router import city_router_app
from api.places_router import places_app;


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow any extension
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(master_data_app)
app.include_router(city_router_app)
app.include_router(places_app)