from fastapi import FastAPI
from Wanderlust.database import Base, engine
from Wanderlust.routes import user_routes

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(user_routes.router)
