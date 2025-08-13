import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================
# Interferogram Constants
# ============================
DATA_PLATFORM = ["Sentinel-1"]
PROCESSING_LEVEL = ["SLC"]
BEAM_MODE = "IW"
RESOLUTION = 60
POLARIZATION = "VV"
WAVELENGTH = 56
COARSEN = (1, 4)
SUBSWATH = 123
PERP_BASELINE_MIN = 10
PERP_BASELINE_MAX = 150
TEMP_BASELINE = 60
SCENES_FILENAME = "scenes.csv"
SCENES_CANDIDATES = "scenes_candidates.csv"

# ============================
# AWS Configuration
# ============================
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME", "glrem-space-geospatial-data")
AWS_PROCESSED_FOLDER = os.getenv("AWS_PROCESSED_FOLDER", "app-analyzed-data")
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

# ============================
# USGS Credentials
# ============================
USGS_ENDPOINT = os.getenv("USGS_ENDPOINT")

# ============================
# SQLALCHEMY_DATABASE_URL
# ============================
SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

# ============================
# USGS
# ============================
USGS_ENDPOINT = os.getenv("USGS_ENDPOINT")
USGS_SHAKEMAP = os.getenv("USGS_SHAKEMAP")
