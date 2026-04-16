
from pydantic import BaseModel

class Login(BaseModel):
    email:str
    password:str
    code:str|None=None

class OTP(BaseModel):
    email:str
    otp:str
