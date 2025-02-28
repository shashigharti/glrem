"""
Main entry point for the FastAPI application. This module configures the app,
sets up CORS middleware, and includes routers for different endpoints.

Routers included:
- /geospatial for geospatial-related endpoints
- /user for user-related endpoints
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.endpoints.geospatial.task import router as task_router
from src.endpoints.admin.user import router as user_router
from src.endpoints.geospatial.earthquake import router as earthquake_router
from src.endpoints.geospatial.flood import router as flood_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(earthquake_router, prefix="/earthquakes", tags=["Earthquakes"])
app.include_router(flood_router, prefix="/floods", tags=["Floods"])
app.include_router(task_router, prefix="/user", tags=["User"])
app.include_router(user_router, prefix="/user", tags=["User"])
