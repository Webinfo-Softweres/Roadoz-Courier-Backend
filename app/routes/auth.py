
from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.schemas.auth import Login,OTP
from app.services.auth_service import login
from app.services.otp_service import send_otp,verify_otp

router=APIRouter()

def db():
    d=SessionLocal()
    yield d

@router.post("/login")
def l(data:Login,db:Session=Depends(db)):
    r=login(db,data.email,data.password,data.code)
    if r=="CODE": return {"msg":"code required"}
    if not r: return {"error":"invalid"}
    return {"access_token":r}

@router.post("/send-otp")
def s(email:str):
    return {"otp":send_otp(email)}

@router.post("/verify-otp")
def v(data:OTP):
    return {"valid":verify_otp(data.email,data.otp)}
