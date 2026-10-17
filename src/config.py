import os
from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"

# Database Configuration
DB_PATH = DATA_DIR / "pipeline.db"
SCHEMA_PATH = SRC_DIR / "pipeline" / "schema.sql"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Application Defaults
DEFAULT_CURRENCY = "INR"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

