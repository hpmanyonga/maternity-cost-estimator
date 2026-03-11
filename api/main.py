"""FastAPI app — serves API + static frontend."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from api.routes import router

app = FastAPI(
    title="Maternity Cost Estimator API",
    description="Network One Health maternity cost estimation engine",
    version="1.0.0",
)

app.include_router(router)

# Mount static files (CSS, JS, assets)
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    """Serve the branded single-page app."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
