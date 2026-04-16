
from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import hash
from app.dependencies.role_checker import role

router=APIRouter()

def db():
    d=SessionLocal()
    yield d

@router.post("")
def create(data:dict,db:Session=Depends(db),u=Depends(role("superadmin"))):
    f=User(**data,role="franchise",password=hash(data["password"]))
    db.add(f); db.commit()
    return f

@router.get("")
def list(search:str="",db:Session=Depends(db)):
    q=db.query(User).filter(User.role=="franchise")
    if search:
        q=q.filter(User.name.contains(search)|User.email.contains(search))
    return q.all()

@router.get("/{id}")
def get(id:int,db:Session=Depends(db)):
    return db.query(User).get(id)

@router.put("/{id}")
def update(id:int,data:dict,db:Session=Depends(db)):
    u=db.query(User).get(id)
    for k,v in data.items(): setattr(u,k,v)
    db.commit(); return u

@router.delete("/{id}")
def delete(id:int,db:Session=Depends(db)):
    u=db.query(User).get(id)
    db.delete(u); db.commit()
    return {"msg":"deleted"}
