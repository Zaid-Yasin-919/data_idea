from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseScraper(ABC):
    """Abstract base class for all procurement and business data scrapers."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def fetch_records(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch raw records matching the search criteria."""
        pass

