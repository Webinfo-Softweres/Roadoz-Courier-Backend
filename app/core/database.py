
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

engine=create_engine("sqlite:///./db.sqlite3", connect_args={"check_same_thread": False})
SessionLocal=sessionmaker(bind=engine)
Base=declarative_base()
