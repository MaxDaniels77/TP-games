import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the project."""
    
    # API Configuration
    RAWG_API_KEY = os.getenv("RAWG_API_KEY")
    BASE_URL = "https://api.rawg.io/api"
    
    # Project Root logic (assuming this file is in src/)
    # src/config.py -> parent is src -> parent is project root
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Data Paths
    DATA_DIR = os.path.join(PROJECT_ROOT, "data")
    BRONZE_PATH = os.path.join(DATA_DIR, "bronze")
    SILVER_PATH = os.path.join(DATA_DIR, "silver")

    @classmethod
    def validate(cls):
        """Validates that critical configuration is present."""
        if not cls.RAWG_API_KEY:
            raise ValueError("RAWG_API_KEY is not set in environment or .env file.")

# Run validation on import to fail fast if config is bad (optional, but good practice)
# Config.validate()
