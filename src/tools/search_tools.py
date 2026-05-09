"""Search tools with Tavily primary and DuckDuckGo fallback."""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio

from ..core.config import settings
from ..core.retry_handler import with_retry

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result data structure."""
    
    title: str
    url: str
    snippet: str
    source: str  # 'tavily' or 'duckduckgo'
    published_date: Optional[str] = None
    score: Optional[float] = None


class SearchTools:
    """
    Search integration with Tavily (primary) and DuckDuckGo (fallback).
    Implements automatic failover and parallel search capabilities.
    """
    
    def __init__(self):
        """Initialize search tools."""
        self.tavily_api_key = settings.tavily_api_key
        self.tavily_available = bool(self.tavily_api_key)
        
        # Import search libraries
        self._setup_search_clients()
        
        logger.info(
            f"SearchTools initialized: Tavily={'enabled' if self.tavily_available else 'disabled'}, "
            f"DuckDuckGo=enabled"
        )
    
    def _setup_search_clients(self) -> None:
        """Setup search client libraries."""
        # Tavily client
        if self.tavily_available:
            try:
                from tavily import TavilyClient
                self.tavily_client = TavilyClient(api_key=self.tavily_api_key)
                logger.info("Tavily client initialized")
            except ImportError:
                logger.warning("Tavily library not installed, using DuckDuckGo only")
                self.tavily_available = False
            except Exception as e:
                logger.error(f"Failed to initialize Tavily client: {str(e)}")
                self.tavily_available = False
        
        # DuckDuckGo client
        try:
            from ddgs import DDGS
            self.ddgs_client = DDGS()
            logger.info("DuckDuckGo client initialized")
        except ImportError:
            logger.error("DDGS library not installed. Install with: pip install ddgs")
            self.ddgs_client = None
        except Exception as e:
            logger.error(f"Failed to initialize DuckDuckGo client: {str(e)}")
            self.ddgs_client = None
    
    @with_retry(max_attempts=2, initial_delay=1)
    def _search_tavily(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic"
    ) -> List[SearchResult]:
        """
        Search using Tavily API.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            search_depth: 'basic' or 'advanced'
            
        Returns:
            List of SearchResult objects
        """
        if not self.tavily_available:
            raise ValueError("Tavily is not available")
        
        logger.info(f"Searching Tavily: {query}")
        
        try:
            response = self.tavily_client.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
                include_answer=False,
                include_raw_content=False
            )
            
            results = []
            for item in response.get('results', []):
                results.append(SearchResult(
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    snippet=item.get('content', ''),
                    source='tavily',
                    published_date=item.get('published_date'),
                    score=item.get('score')
                ))
            
            logger.info(f"Tavily returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Tavily search failed: {str(e)}")
            raise
    
    @with_retry(max_attempts=2, initial_delay=1)
    def _search_duckduckgo(
        self,
        query: str,
        max_results: int = 5
    ) -> List[SearchResult]:
        """
        Search using DuckDuckGo.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of SearchResult objects
        """
        if not self.ddgs_client:
            raise ValueError("DuckDuckGo is not available")
        
        logger.info(f"Searching DuckDuckGo: {query}")
        
        try:
            results = []
            ddgs_results = self.ddgs_client.text(
                keywords=query,
                max_results=max_results
            )
            
            for item in ddgs_results:
                results.append(SearchResult(
                    title=item.get('title', ''),
                    url=item.get('href', ''),
                    snippet=item.get('body', ''),
                    source='duckduckgo'
                ))
            
            logger.info(f"DuckDuckGo returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {str(e)}")
            raise
    
    def search(
        self,
        query: str,
        max_results: int = 5,
        use_fallback: bool = True
    ) -> List[SearchResult]:
        """
        Search with automatic fallback from Tavily to DuckDuckGo.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            use_fallback: Whether to use fallback on failure
            
        Returns:
            List of SearchResult objects
        """
        # Try Tavily first
        if self.tavily_available:
            try:
                return self._search_tavily(query, max_results)
            except Exception as e:
                logger.warning(f"Tavily search failed, trying fallback: {str(e)}")
                if not use_fallback:
                    raise
        
        # Fallback to DuckDuckGo
        if self.ddgs_client:
            try:
                return self._search_duckduckgo(query, max_results)
            except Exception as e:
                logger.error(f"DuckDuckGo search also failed: {str(e)}")
                raise
        
        raise RuntimeError("No search providers available")
    
    def search_company_news(
        self,
        company_name: str,
        max_results: int = 5
    ) -> List[SearchResult]:
        """
        Search for recent company news.
        
        Args:
            company_name: Company name
            max_results: Maximum number of results
            
        Returns:
            List of SearchResult objects
        """
        query = f"{company_name} news recent announcements"
        return self.search(query, max_results)
    
    def search_industry_trends(
        self,
        industry: str,
        max_results: int = 3
    ) -> List[SearchResult]:
        """
        Search for industry trends.
        
        Args:
            industry: Industry name
            max_results: Maximum number of results
            
        Returns:
            List of SearchResult objects
        """
        query = f"{industry} industry trends 2024"
        return self.search(query, max_results)
    
    def search_person_info(
        self,
        person_name: str,
        company: Optional[str] = None,
        max_results: int = 3
    ) -> List[SearchResult]:
        """
        Search for information about a person.
        
        Args:
            person_name: Person's name
            company: Optional company name for context
            max_results: Maximum number of results
            
        Returns:
            List of SearchResult objects
        """
        query = f"{person_name}"
        if company:
            query += f" {company}"
        query += " professional background"
        
        return self.search(query, max_results)
    
    async def parallel_search(
        self,
        queries: List[str],
        max_results: int = 5
    ) -> Dict[str, List[SearchResult]]:
        """
        Execute multiple searches in parallel.
        
        Args:
            queries: List of search queries
            max_results: Maximum results per query
            
        Returns:
            Dictionary mapping queries to results
        """
        async def search_async(query: str) -> tuple[str, List[SearchResult]]:
            """Async wrapper for search."""
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self.search,
                query,
                max_results
            )
            return query, results
        
        # Execute searches in parallel
        tasks = [search_async(query) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build results dictionary
        search_results = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Parallel search failed: {str(result)}")
                continue
            query, query_results = result
            search_results[query] = query_results
        
        return search_results
    
    def format_results_for_llm(self, results: List[SearchResult]) -> str:
        """
        Format search results for LLM consumption.
        
        Args:
            results: List of search results
            
        Returns:
            Formatted string
        """
        if not results:
            return "No search results found."
        
        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(
                f"{i}. {result.title}\n"
                f"   URL: {result.url}\n"
                f"   {result.snippet}\n"
                f"   Source: {result.source}"
            )
            if result.published_date:
                formatted[-1] += f"\n   Published: {result.published_date}"
        
        return "\n\n".join(formatted)


# Global search tools instance
search_tools = SearchTools()

# Made with Bob
