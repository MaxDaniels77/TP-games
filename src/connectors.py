import time
import logging
import requests
from typing import Optional, Dict, Any
from .config import Config

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class RawgApiClient:
    """
    A robust client for interacting with the RAWG Video Games API.
    
    Attributes:
        session (requests.Session): The persistent HTTP session.
        base_url (str): The base URL for the API.
        api_key (str): The API key for authentication.
    """

    def __init__(self):
        """Initializes the RawgApiClient with a session and default headers."""
        self.base_url = Config.BASE_URL
        self.api_key = Config.RAWG_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "RawgDataPipeline/1.0 (Educational Project)"
        })
        
        if not self.api_key:
            logger.warning("RAWG_API_KEY is missing. API calls will likely fail.")

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Internal method to perform GET requests with rate limiting and error handling.

        Args:
            endpoint (str): The API endpoint to query (e.g., 'games').
            params (dict, optional): Query parameters.

        Returns:
            Optional[Dict[str, Any]]: The JSON response dictionary, or None on failure.
        """
        url = f"{self.base_url}/{endpoint}"
        
        if params is None:
            params = {}
        
        # Inject API Key automatically
        params["key"] = self.api_key
        
        # Rate Limiting: Sleep 0.6 seconds before request
        # RAWG allows limited requests, so this helps avoid immediate 429s.
        time.sleep(0.6)

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error querying {url}: {e.response.status_code} - {e.response.text}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection Error querying {url}: {e}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout Error querying {url}: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Unexpected Request Error querying {url}: {e}")
            
        return None
