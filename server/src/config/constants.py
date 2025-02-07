import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================
# Default Constants
# ============================
DATA_PLATFORM = ["Sentinel-1"]
PROCESSING_LEVEL = ["SLC"]
BEAM_MODE = "IW"
RESOLUTION = 200.0
SUBSWATH = 3
USE_BURST = False

# ============================
# AWS Configuration
# ============================
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME", "guardian-space-geospatial-data")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")

# ============================
# ASF Credentials
# ============================
ASF_USERNAME = os.getenv("ASF_USERNAME")
ASF_PASSWORD = os.getenv("ASF_PASSWORD")

# ============================
# Directories
# ============================
WORKDIR = os.getenv("WORKDIR", "/data/workdir")
DATADIR = os.getenv("DATADIR", "/data/datadir")
OUTPUT = os.getenv("OUTPUT", "/data/output")

# ============================
# Logging Configuration
# ============================
LOG_FILENAME = os.getenv("LOG_FILENAME", "app.log")
