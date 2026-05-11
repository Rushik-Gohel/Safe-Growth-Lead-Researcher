"""Search tools with Tavily primary and DuckDuckGo fallback."""

import logging
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio

from ..core.config import settings
from ..core.retry_handler import with_retry
from ..core.cache import cached, get_cache_stats

logger = logging.getLogger(__name__)

# Mock mode for testing (set MOCK_SEARCH=true in environment)
MOCK_MODE = os.getenv("MOCK_SEARCH", "false").lower() == "true"


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
    
    @cached(ttl=settings.search_cache_ttl, key_prefix="tavily")
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
    
    @cached(ttl=settings.search_cache_ttl, key_prefix="ddg")
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
        if MOCK_MODE:
            logger.info(f"MOCK MODE: Generating mock company news for {company_name}")
            return self._generate_mock_company_news_cached(company_name, max_results)
        
        return self._search_company_news_cached(company_name, max_results)
    
    @cached(ttl=settings.company_news_cache_ttl, key_prefix="company_news")
    def _search_company_news_cached(
        self,
        company_name: str,
        max_results: int = 5
    ) -> List[SearchResult]:
        """Internal cached method for company news search."""
        query = f"{company_name} news recent announcements"
        return self.search(query, max_results)
    
    @cached(ttl=settings.company_news_cache_ttl, key_prefix="company_news_mock")
    def _generate_mock_company_news_cached(
        self,
        company_name: str,
        max_results: int
    ) -> List[SearchResult]:
        """Internal cached method for mock company news."""
        return self._generate_mock_company_news(company_name, max_results)
    
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
        if MOCK_MODE:
            logger.info(f"MOCK MODE: Generating mock industry trends for {industry}")
            return self._generate_mock_industry_trends_cached(industry, max_results)
        
        return self._search_industry_trends_cached(industry, max_results)
    
    @cached(ttl=settings.industry_trends_cache_ttl, key_prefix="industry_trends")
    def _search_industry_trends_cached(
        self,
        industry: str,
        max_results: int = 3
    ) -> List[SearchResult]:
        """Internal cached method for industry trends search."""
        query = f"{industry} industry trends 2024"
        return self.search(query, max_results)
    
    @cached(ttl=settings.industry_trends_cache_ttl, key_prefix="industry_trends_mock")
    def _generate_mock_industry_trends_cached(
        self,
        industry: str,
        max_results: int
    ) -> List[SearchResult]:
        """Internal cached method for mock industry trends."""
        return self._generate_mock_industry_trends(industry, max_results)
    
    def _generate_mock_company_news(self, company_name: str, max_results: int) -> List[SearchResult]:
        """Generate mock company news for testing."""
        mock_news = [
            SearchResult(
                title=f"{company_name} Announces Q4 2024 Results",
                url=f"https://example.com/news/{company_name.lower()}-q4-results",
                snippet=f"{company_name} reported strong Q4 2024 results with revenue growth of 15% year-over-year. The company exceeded analyst expectations across all key metrics.",
                source="mock",
                published_date="2024-01-15"
            ),
            SearchResult(
                title=f"{company_name} Launches New Product Line",
                url=f"https://example.com/news/{company_name.lower()}-new-product",
                snippet=f"{company_name} unveiled its latest product innovation at the annual conference. The new offering is expected to capture significant market share in the coming quarters.",
                source="mock",
                published_date="2024-01-10"
            ),
            SearchResult(
                title=f"{company_name} Expands Global Operations",
                url=f"https://example.com/news/{company_name.lower()}-expansion",
                snippet=f"{company_name} announced plans to expand operations into three new international markets. The expansion is part of the company's strategic growth initiative.",
                source="mock",
                published_date="2024-01-05"
            ),
            SearchResult(
                title=f"{company_name} Partners with Industry Leader",
                url=f"https://example.com/news/{company_name.lower()}-partnership",
                snippet=f"{company_name} formed a strategic partnership with a leading technology provider. The collaboration aims to enhance customer experience and drive innovation.",
                source="mock",
                published_date="2023-12-28"
            ),
            SearchResult(
                title=f"{company_name} Wins Industry Award",
                url=f"https://example.com/news/{company_name.lower()}-award",
                snippet=f"{company_name} received the prestigious Industry Excellence Award for innovation and customer satisfaction. This marks the third consecutive year the company has been recognized.",
                source="mock",
                published_date="2023-12-20"
            ),
        ]
        return mock_news[:max_results]
    
    def _generate_mock_industry_trends(self, industry: str, max_results: int) -> List[SearchResult]:
        """Generate mock industry trends for testing."""
        mock_trends = [
            SearchResult(
                title=f"Top {industry} Trends for 2024",
                url=f"https://example.com/trends/{industry.lower()}-2024",
                snippet=f"The {industry} industry is experiencing rapid transformation driven by AI, automation, and changing customer expectations. Companies are investing heavily in digital transformation initiatives.",
                source="mock",
                published_date="2024-01-01"
            ),
            SearchResult(
                title=f"How AI is Reshaping the {industry} Industry",
                url=f"https://example.com/trends/ai-{industry.lower()}",
                snippet=f"Artificial intelligence is revolutionizing the {industry} sector. From predictive analytics to automated workflows, AI adoption is accelerating across the industry.",
                source="mock",
                published_date="2023-12-15"
            ),
            SearchResult(
                title=f"{industry} Market Outlook 2024-2025",
                url=f"https://example.com/trends/{industry.lower()}-outlook",
                snippet=f"Industry analysts predict strong growth for the {industry} sector over the next two years. Key drivers include technological innovation, market expansion, and increased investment.",
                source="mock",
                published_date="2023-12-10"
            ),
        ]
        return mock_trends[:max_results]
    
    @cached(ttl=settings.cache_ttl, key_prefix="person_info")
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


