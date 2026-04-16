
from app.models.user import User
from app.core.security import verify
from app.utils.jwt import create

def login(db,email,password,code=None):
    u=db.query(User).filter(User.email==email).first()
    if not u or not verify(password,u.password): return None
    if u.role=="franchise" and u.franchise_code!=code:
        return "CODE"
    return create({"user_id":u.id,"email":u.email,"role":u.role})
