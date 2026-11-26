"""
CONCILIA AI - FastAPI Main Application & Static Frontend Server
Serves both the REST API and the pre-compiled Next.js frontend.
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import init_db
from app.api.routes import router

# CONCILIA_V5_LOCAL_SECURITY_30A5A
from app.local_security_v5 import (
    ALLOWED_ORIGINS,
    LocalSecurityMiddlewareV5,
    safe_static_path
)

app = FastAPI(
    title="CONCILIA AI",
    description="Sistema Profissional de Conciliação Contábil Automática com Auditoria Matemática",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

app.add_middleware(LocalSecurityMiddlewareV5)


@app.on_event("startup")
def startup_event():
    init_db()

# Include REST API router
app.include_router(router)

# Locate frontend static build directory
# Check in bundled PyInstaller sys._MEIPASS or standard relative paths
if hasattr(sys, "_MEIPASS"):
    STATIC_DIR = Path(sys._MEIPASS) / "frontend_out"
else:
    STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "out"

if STATIC_DIR.exists():
    app.mount("/_next", StaticFiles(directory=str(STATIC_DIR / "_next")), name="next_static")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Don't intercept API calls
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(
                status_code=404,
                detail="Rota nao encontrada."
            )
        try:
            file_path = safe_static_path(
                STATIC_DIR,
                full_path
            )
        except (ValueError, OSError):
            raise HTTPException(
                status_code=403,
                detail="Caminho nao autorizado."
            )
        if file_path.is_file():
            return FileResponse(file_path)
        try:
            index_file = safe_static_path(
                STATIC_DIR,
                "index.html"
            )
        except (ValueError, OSError):
            raise HTTPException(
                status_code=403,
                detail="Caminho nao autorizado."
            )
        if index_file.exists():
            return FileResponse(index_file)
        return {"error": "Frontend build not found"}
else:
    @app.get("/")
    def index():
        return {
            "app": "CONCILIA AI Backend",
            "status": "Online",
            "docs": "/docs",
            "message": "Frontend static files not found."
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
