
from passlib.context import CryptContext
pwd=CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash(p): return pwd.hash(p)
def verify(p,h): return pwd.verify(p,h)
