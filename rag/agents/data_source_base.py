from abc import ABC, abstractmethod
from typing import List


class DataSourceBase(ABC):
    @abstractmethod
    def fetch(self, query: str) -> List[str]:
        """Fetch relevant data for a query"""

    def health_check(self) -> bool:
        """Check if data source is available"""
        return True
