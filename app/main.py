
from fastapi import FastAPI
from app.routes import auth,franchise,profile,websocket
from app.core.database import Base,engine

Base.metadata.create_all(bind=engine)

app=FastAPI()

app.include_router(auth.router,prefix="/api/v1/auth")
app.include_router(franchise.router,prefix="/api/v1/franchise")
app.include_router(profile.router,prefix="/api/v1/profile")
app.include_router(websocket.router)
