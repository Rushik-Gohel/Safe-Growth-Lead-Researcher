"""Test script to debug LinkedIn scraping."""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Import after path setup
from src.tools.linkedin_scraper import linkedin_scraper

def test_linkedin_scraper():
    """Test LinkedIn scraper with a sample URL."""
    logger.info("Starting LinkedIn scraper test...")
    
    # Test with a LinkedIn URL
    test_url = "https://www.linkedin.com/in/test-profile"
    
    logger.info(f"Testing with URL: {test_url}")
    profile = linkedin_scraper.scrape_profile(test_url)
    
    logger.info(f"Profile result:")
    logger.info(f"  - URL: {profile.url}")
    logger.info(f"  - Name: {profile.name}")
    logger.info(f"  - Title: {profile.title}")
    logger.info(f"  - Company: {profile.company}")
    logger.info(f"  - Error: {profile.error}")
    logger.info(f"  - Is Valid: {profile.is_valid}")
    
    if profile.error:
        logger.warning(f"LinkedIn scraping failed: {profile.error}")
    else:
        logger.info("LinkedIn scraping succeeded!")
    
    return profile

if __name__ == "__main__":
    test_linkedin_scraper()

# Made with Bob
