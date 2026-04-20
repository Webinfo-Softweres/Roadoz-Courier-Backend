from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.database import init_db
from app.core.security import get_password_hash
from app.middleware.auth_middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from app.routes import auth, franchise, profile, websocket

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def _seed_super_admin():
    """Create the super admin user if it doesn't already exist."""
    from app.core.database import AsyncSessionLocal
    from app.models.user import User, UserRole
    from sqlalchemy import select
    import uuid

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == settings.SUPER_ADMIN_EMAIL))
        if not result.scalar_one_or_none():
            admin = User(
                id=str(uuid.uuid4()),
                name=settings.SUPER_ADMIN_NAME,
                email=settings.SUPER_ADMIN_EMAIL,
                password_hash=get_password_hash(settings.SUPER_ADMIN_PASSWORD),
                role=UserRole.SUPER_ADMIN.value,  # store as string for SQLite
            )
            db.add(admin)
            await db.commit()
            logger.info(f"Super admin created: {settings.SUPER_ADMIN_EMAIL}")
        else:
            logger.info("Super admin already exists")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    # init_db auto-creates all tables (works for SQLite out of the box)
    await init_db()
    await _seed_super_admin()
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## FastAPI JWT Authentication & Franchise Management System

### Features
- **Unified login** for Super Admin and Franchise users
- **JWT authentication** with access & refresh tokens
- **Franchise CRUD** with pagination and search
- **OTP verification** via SMTP email or Twilio SMS
- **Redis caching** for sessions, OTPs, and franchise data
- **WebSocket** real-time notifications at `/ws/notifications`
- **Role-based access control** (Super Admin / Franchise)
- **SQLite** by default — swap `DATABASE_URL` for PostgreSQL in production
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, exc: IntegrityError):
    logger.exception("IntegrityError", exc_info=exc)
    return JSONResponse(status_code=409, content={"detail": "Database constraint violated"})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

from fastapi.staticfiles import StaticFiles

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ── Middleware ───────────────────────────────────────────────────────────────


origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://admin.roadozcourier.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# ── Routers ──────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"
app.include_router(auth.router,      prefix=API_PREFIX)
app.include_router(franchise.router, prefix=API_PREFIX)
app.include_router(profile.router,   prefix=API_PREFIX)
app.include_router(websocket.router)


@app.get("/", tags=["Health"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "database": "SQLite (franchise.db)" if settings.DATABASE_URL.startswith("sqlite") else "PostgreSQL",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
