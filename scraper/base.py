from abc import ABC, abstractmethod
from typing import Dict, Any

class PriceExtractionError(Exception):
    pass

class BaseScraper(ABC):
    @abstractmethod
    async def fetch_product_data(self, url: str) -> Dict[str, Any]:
        """
        Takes a product URL and returns a dictionary with:
        - product_id (str)
        - current_price (float)
        - mrp_shown (float)
        - title (str)
        - platform (str)
        
        Raises PriceExtractionError if the price or mrp cannot be extracted.
        """
        pass
