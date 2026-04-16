
from sqlalchemy import Column,Integer,String
from app.core.database import Base

class User(Base):
    __tablename__="users"
    id=Column(Integer,primary_key=True)
    name=Column(String)
    email=Column(String,unique=True)
    password=Column(String)
    role=Column(String)
    phone=Column(String)
    address=Column(String)
    franchise_code=Column(String,unique=True,nullable=True)
