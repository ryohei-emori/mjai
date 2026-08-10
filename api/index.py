"""
Vercel Python serverless function entrypoint.

This file exposes the FastAPI app to Vercel's Python runtime.
Vercel detects the `app` variable and serves it as a serverless function.
"""
import sys
from pathlib import Path

# Add backend directory to Python path for imports
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Import the FastAPI app from the existing backend module
from app.main import app

# Vercel expects a variable named `app` at module level
__all__ = ["app"]
