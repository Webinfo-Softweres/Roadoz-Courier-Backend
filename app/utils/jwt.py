
import jwt
from datetime import datetime,timedelta
from app.core.config import SECRET_KEY,ALGORITHM

def create(data):
    data["exp"]=datetime.utcnow()+timedelta(minutes=30)
    return jwt.encode(data,SECRET_KEY,algorithm=ALGORITHM)

def decode(t):
    return jwt.decode(t,SECRET_KEY,algorithms=[ALGORITHM])
