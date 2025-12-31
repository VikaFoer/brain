"""
Script to run the application
"""
import os
import uvicorn

if __name__ == "__main__":
    # Railway надає PORT через змінну оточення
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    # В продакшені не використовуємо reload
    reload = os.environ.get("DEBUG", "false").lower() == "true"
    
    print(f"Starting server on {host}:{port}")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

