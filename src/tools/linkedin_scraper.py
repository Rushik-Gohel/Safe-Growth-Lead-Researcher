"""LinkedIn profile scraper with rate limiting and caching."""

import re
import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
import requests
from bs4 import BeautifulSoup

from ..core.config import settings
from ..core.retry_handler import with_retry
from ..core.cache import cached

logger = logging.getLogger(__name__)


@dataclass
class LinkedInProfile:
    """LinkedIn profile data structure."""
    
    url: str
    name: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    experience: Optional[str] = None
    education: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @property
    def is_valid(self) -> bool:
        """Check if profile has valid data."""
        return self.name is not None and self.error is None


class LinkedInScraper:
    """
    LinkedIn profile scraper with rate limiting and error handling.
    
    Note: This is a simplified implementation. In production, consider:
    - Using official LinkedIn API
    - Implementing proper authentication
    - Respecting robots.txt
    - Using a headless browser for JavaScript-rendered content
    """
    
    def __init__(self, rate_limit_delay: float = 2.0):
        """
        Initialize LinkedIn scraper.
        
        Args:
            rate_limit_delay: Delay between requests in seconds
        """
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0.0
        
        # User agent to avoid blocking
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        
        logger.info(f"LinkedInScraper initialized with {rate_limit_delay}s rate limit")
    
    def _validate_linkedin_url(self, url: str) -> bool:
        """
        Validate if URL is a LinkedIn profile URL.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid LinkedIn URL
        """
        linkedin_pattern = r'https?://(www\.)?linkedin\.com/in/[\w-]+'
        return bool(re.match(linkedin_pattern, url))
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize LinkedIn URL.
        
        Args:
            url: Raw URL
            
        Returns:
            Normalized URL
        """
        # Remove trailing slashes
        url = url.rstrip('/')
        
        # Ensure https
        if url.startswith('http://'):
            url = url.replace('http://', 'https://')
        elif not url.startswith('https://'):
            url = f'https://{url}'
        
        return url
    
    def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    @with_retry(max_attempts=3, initial_delay=2)
    def _fetch_page(self, url: str) -> str:
        """
        Fetch page content with retry logic.
        
        Args:
            url: URL to fetch
            
        Returns:
            Page HTML content
            
        Raises:
            requests.RequestException: If request fails
        """
        self._rate_limit()
        
        logger.debug(f"Fetching LinkedIn profile: {url}")
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        
        return response.text
    
    def _parse_profile(self, html: str, url: str) -> LinkedInProfile:
        """
        Parse LinkedIn profile from HTML.
        
        Args:
            html: Page HTML content
            url: Profile URL
            
        Returns:
            LinkedInProfile object
        """
        soup = BeautifulSoup(html, 'lxml')
        
        profile = LinkedInProfile(url=url)
        
        try:
            # Check if we got a login page or error page
            if 'authwall' in html.lower() or 'sign in' in html.lower()[:1000]:
                profile.error = "LinkedIn requires authentication - cannot scrape without login"
                logger.warning("LinkedIn returned login/auth wall")
                return profile
            
            # Note: LinkedIn's HTML structure changes frequently
            # This is a simplified example - adjust selectors as needed
            
            # Extract name
            name_elem = soup.find('h1', class_='text-heading-xlarge')
            if name_elem:
                profile.name = name_elem.get_text(strip=True)
            
            # Extract title
            title_elem = soup.find('div', class_='text-body-medium')
            if title_elem:
                profile.title = title_elem.get_text(strip=True)
            
            # Extract company (from title or separate element)
            if profile.title and ' at ' in profile.title:
                parts = profile.title.split(' at ')
                if len(parts) == 2:
                    profile.title = parts[0].strip()
                    profile.company = parts[1].strip()
            
            # Extract location
            location_elem = soup.find('span', class_='text-body-small')
            if location_elem:
                profile.location = location_elem.get_text(strip=True)
            
            # Extract bio/about
            about_elem = soup.find('div', class_='display-flex ph5 pv3')
            if about_elem:
                profile.bio = about_elem.get_text(strip=True)[:500]  # Limit length
            
            # Check if we got any data
            if not profile.name and not profile.title:
                profile.error = "Could not extract profile data - LinkedIn may have blocked the request or changed their HTML structure"
                logger.warning("No profile data extracted from HTML")
            else:
                logger.info(f"Successfully parsed profile: {profile.name or 'Unknown'}")
            
        except Exception as e:
            logger.error(f"Error parsing profile: {str(e)}")
            profile.error = f"Parsing error: {str(e)}"
        
        return profile
    
    @cached(ttl=settings.linkedin_cache_ttl, key_prefix="linkedin")
    def scrape_profile(self, url: str) -> LinkedInProfile:
        """
        Scrape LinkedIn profile with caching.
        
        Args:
            url: LinkedIn profile URL
            
        Returns:
            LinkedInProfile object
        """
        # Normalize URL
        url = self._normalize_url(url)
        
        # Validate URL
        if not self._validate_linkedin_url(url):
            logger.warning(f"Invalid LinkedIn URL: {url}")
            return LinkedInProfile(
                url=url,
                error="Invalid LinkedIn profile URL"
            )
        
        try:
            # Fetch page
            html = self._fetch_page(url)
            
            # Parse profile
            profile = self._parse_profile(html, url)
            
            return profile
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch LinkedIn profile: {str(e)}")
            return LinkedInProfile(
                url=url,
                error=f"Network error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error scraping profile: {str(e)}")
            return LinkedInProfile(
                url=url,
                error=f"Scraping error: {str(e)}"
            )
    
    def extract_profile_from_text(self, text: str) -> Optional[str]:
        """
        Extract LinkedIn profile URL from text.
        
        Args:
            text: Text that may contain a LinkedIn URL
            
        Returns:
            Extracted URL or None
        """
        pattern = r'https?://(?:www\.)?linkedin\.com/in/[\w-]+'
        match = re.search(pattern, text)
        
        if match:
            return match.group(0)
        
        return None


# Global scraper instance
linkedin_scraper = LinkedInScraper()

# Made with Bob
