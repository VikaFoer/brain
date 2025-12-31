"""
Main FastAPI application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api import router as api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.models import Category, LegalAct, Subset, ActCategory, ActRelation
import os

app = FastAPI(
    title=settings.APP_NAME,
    description="Система аналізу нормативно-правових актів України",
    version="1.0.0"
)

# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    """Create database tables if they don't exist"""
    try:
        # Check if database is accessible
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created/verified")
    except Exception as e:
        print(f"⚠️  Database initialization warning: {e}")
        print("⚠️  Application will continue but database features may not work")
        # Don't raise - allow app to start even if DB fails

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшені обмежити
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api")

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Serve frontend files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")

@app.get("/favicon.ico")
async def favicon():
    """Serve favicon"""
    return {"detail": "No favicon"}

@app.get("/")
async def root():
    return {
        "message": "Legal Graph System API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "online"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/status")
async def status():
    """Redirect to API status endpoint"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/status")

@app.get("/admin")
async def admin_panel():
    """Admin panel interface"""
    admin_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "admin.html")
    if os.path.exists(admin_file):
        return FileResponse(admin_file)
    raise HTTPException(status_code=404, detail="Admin panel not found")

@app.get("/app")
async def main_app():
    """Main application interface"""
    app_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
    if os.path.exists(app_file):
        return FileResponse(app_file)
    raise HTTPException(status_code=404, detail="Application not found")

