import requests
from Qai.rag.agents.data_source_base import DataSourceBase
from Qai.rag.utils.logger import logger
import time
from typing import List


class WebResearchAgent(DataSourceBase):
    def __init__(
        self, endpoint: str = "http://localhost:8083/websearch", timeout: int = 10
    ):
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        logger.info(f"WebResearchAgent initialized with endpoint {self.endpoint}")

    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self.endpoint}/health", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def fetch(self, query: str) -> List[str]:
        if not query.strip():
            return []

        logger.info(f"Searching web for: {query[:50]}...")
        start_time = time.time()

        try:
            response = requests.post(
                f"{self.endpoint}/search",
                json={"query": query, "limit": 7},
                timeout=self.timeout,
            )
            response.raise_for_status()
            search_results = response.json()

            results = search_results.get("search_results", [])
            if not results:
                logger.info(f"No results found for '{query}'")
                return []

            formatted = [
                f"Source: {res.get('source', 'Unknown')}\n"
                f"Title: {res.get('title', 'Untitled')}\n"
                f"Summary: {res.get('snippet', 'No summary available')}"
                for res in results
            ]

            logger.info(
                f"Found {len(formatted)} results in {time.time()-start_time:.2f}s"
            )
            return formatted

        except requests.exceptions.Timeout:
            logger.warning(f"Web search timed out for '{query}'")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Web search failed: {e}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected error in web search: {e}")
            return []
