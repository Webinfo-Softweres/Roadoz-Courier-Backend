
from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.dependencies.role_checker import current
from app.models.user import User

router=APIRouter()

def db():
    d=SessionLocal()
    yield d

@router.get("")
def get(u=Depends(current),db:Session=Depends(db)):
    return db.query(User).get(u["user_id"])
