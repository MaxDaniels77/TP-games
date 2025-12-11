import time
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Dict, Any
from .config import Config

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
        """Initializes the RawgApiClient with a session, default headers, and retry strategy."""
        self.base_url = Config.BASE_URL
        self.api_key = Config.RAWG_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "RawgDataPipeline/1.0 (Educational Project)"
        })
        
        if not self.api_key:
            logger.warning("RAWG_API_KEY is missing. API calls will likely fail.")

        # Configure Retry Strategy
        retry_strategy = Retry(
            total=3,  # Total number of retries
            backoff_factor=1,  # Wait 1s, 2s, 4s...
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these status codes
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def get_resource(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform GET requests with automatic retries and error handling.

        Args:
            endpoint (str): The API endpoint to query (e.g., 'games').
            params (dict, optional): Query parameters.

        Returns:
            Dict[str, Any]: The JSON response dictionary.

        Raises:
            requests.exceptions.RequestException: If the request fails after retries.
        """
        url = f"{self.base_url}/{endpoint}"
        
        if params is None:
            params = {}
        
        # Inject API Key automatically
        params["key"] = self.api_key
        
        # Rate Limiting: Sleep 0.6 seconds before request to be nice to the API
        # Even with retries, it's good practice not to hammer the API.
        time.sleep(0.6)

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error querying {url}: {e.response.status_code} - {e.response.text}")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection Error querying {url}: {e}")
            raise
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout Error querying {url}: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Unexpected Request Error querying {url}: {e}")
            raise
