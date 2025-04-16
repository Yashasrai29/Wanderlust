from sqlalchemy import Column, String
import uuid
from Wanderlust.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    name = Column(String)
    phno = Column(String)
    email = Column(String)
    hashed_password = Column(String)
    role = Column(String, default="user")
