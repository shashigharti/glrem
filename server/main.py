"""
Main entry point for the FastAPI application. This module configures the app,
sets up CORS middleware, and includes routers for different endpoints.

Routers included:
- /geospatial for geospatial-related endpoints
- /user for user-related endpoints
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.endpoints.geospatial.interferogram import router as interferogram_router
from src.endpoints.geospatial.task import router as task_router
from src.endpoints.admin.user import router as user_router
from src.endpoints.geospatial.artifact import router as artifact_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(artifact_router, prefix="/geospatial", tags=["Geospatial"])
app.include_router(task_router, prefix="/geospatial", tags=["Geospatial"])
app.include_router(interferogram_router, prefix="/geospatial", tags=["Geospatial"])
app.include_router(user_router, prefix="/user", tags=["User"])
