# UI entrypoint kept stable for Uvicorn; routes live in ui_routes.py
from app.ui_routes import app  # noqa: F401
