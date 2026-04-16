
from fastapi import Depends,HTTPException
from fastapi.security import HTTPBearer
from app.utils.jwt import decode

sec=HTTPBearer()

def current(token=Depends(sec)):
    try: return decode(token.credentials)
    except: raise HTTPException(401,"Invalid token")

def role(role):
    def r(u=Depends(current)):
        if u["role"]!=role: raise HTTPException(403,"Forbidden")
        return u
    return r
