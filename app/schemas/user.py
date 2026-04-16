
from pydantic import BaseModel

class UpdateUser(BaseModel):
    name:str|None=None
    phone:str|None=None
    address:str|None=None
    password:str|None=None
