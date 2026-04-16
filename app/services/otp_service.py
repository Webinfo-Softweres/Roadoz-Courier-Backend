
from app.utils.otp import generate
from app.utils.redis import r

def send_otp(email):
    otp=generate()
    r.setex(email,300,otp)
    return otp

def verify_otp(email,otp):
    return r.get(email)==otp
