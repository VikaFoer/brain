"""
Main FastAPI application
"""
from fastapi import FastAPI, HTTPException
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
    import logging
    logger = logging.getLogger(__name__)
    
    # Check database type
    database_url = settings.DATABASE_URL or "sqlite:///./legal_db.db"
    is_sqlite = database_url.startswith("sqlite")
    
    if is_sqlite:
        logger.warning("⚠️  WARNING: Using SQLite database!")
        logger.warning("⚠️  SQLite data will be LOST on Railway after each deploy!")
        logger.warning("⚠️  DATABASE_URL is not set or not connected!")
        logger.warning("⚠️  SOLUTION: In Railway Dashboard → 'brain' service → Variables → Add DATABASE_URL")
        logger.warning("⚠️  Use Reference to connect from PostgreSQL service → DATABASE_URL")
        logger.warning("⚠️  See FIX_SQLITE_NOW.md for step-by-step instructions")
        print("⚠️  WARNING: SQLite will lose data on Railway!")
        print("⚠️  DATABASE_URL is not connected! See FIX_SQLITE_NOW.md")
    else:
        logger.info("✔ Using PostgreSQL database (persistent)")
        print("✔ Using PostgreSQL database (persistent)")
    
    try:
        # Check if database is accessible
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("✔ Database tables created/verified")
        print("✅ Database tables created/verified")
        
        # Check if categories exist (only for PostgreSQL)
        if not is_sqlite:
            from app.core.database import SessionLocal
            from app.models.category import Category
            from app.services.processing_service import ProcessingService
            import asyncio
            
            db = SessionLocal()
            try:
                category_count = db.query(Category).count()
                if category_count == 0:
                    logger.warning("⚠️  No categories found in database!")
                    logger.info("🔄 Attempting to auto-initialize categories...")
                    print("⚠️  No categories found! Auto-initializing...")
                    
                    # Try to auto-initialize categories
                    try:
                        processing_service = ProcessingService(db)
                        asyncio.run(processing_service.initialize_categories())
                        db.commit()
                        
                        # Check again
                        new_count = db.query(Category).count()
                        if new_count > 0:
                            logger.info(f"✅ Successfully auto-initialized {new_count} categories!")
                            print(f"✅ Auto-initialized {new_count} categories!")
                        else:
                            logger.warning("⚠️  Auto-initialization failed, please initialize manually")
                            print("⚠️  Auto-initialization failed. Please initialize: POST /api/legal-acts/initialize-categories")
                    except Exception as init_error:
                        logger.error(f"Error auto-initializing categories: {init_error}")
                        logger.warning("⚠️  Please initialize manually: POST /api/legal-acts/initialize-categories")
                        print(f"⚠️  Auto-initialization error: {init_error}")
                        print("⚠️  Please initialize manually: POST /api/legal-acts/initialize-categories")
                else:
                    logger.info(f"✔ Found {category_count} categories in database")
                    print(f"✔ Found {category_count} categories in database")
            except Exception as e:
                logger.debug(f"Could not check categories: {e}")
            finally:
                db.close()
    except Exception as e:
        logger.error(f"✗ Database initialization error: {e}")
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
    print(f"📁 Serving frontend files from: {frontend_dir}")
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

