"""Test mock email generation mode."""

import logging
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set mock mode BEFORE importing anything
os.environ["MOCK_EMAIL_GENERATION"] = "true"
os.environ["MOCK_SEARCH"] = "true"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Import after environment setup
from src.agent.workflow import lead_research_agent

def test_mock_workflow():
    """Test workflow with mock email generation."""
    logger.info("=" * 80)
    logger.info("Testing workflow with MOCK EMAIL GENERATION")
    logger.info("=" * 80)
    
    company_name = "TestCorp"
    
    logger.info(f"\nResearching: {company_name}")
    logger.info("-" * 80)
    
    try:
        result = lead_research_agent.run(company_name)
        
        logger.info("\n" + "=" * 80)
        logger.info("RESULTS:")
        logger.info("=" * 80)
        
        logger.info(f"\n✓ Validation: {'Passed' if result.get('is_valid') else 'Failed'}")
        logger.info(f"✓ Company News: {len(result.get('company_news', []))} articles")
        logger.info(f"✓ Industry Trends: {len(result.get('industry_trends', []))} articles")
        logger.info(f"✓ Email Generated: {'Yes' if result.get('email') else 'No'}")
        logger.info(f"✓ Total Time: {result.get('total_time', 0):.2f}s")
        
        if result.get('email'):
            logger.info("\n" + "=" * 80)
            logger.info("MOCK EMAIL:")
            logger.info("=" * 80)
            logger.info(result['email'])
            logger.info("=" * 80)
        
        logger.info("\n✅ MOCK MODE TEST PASSED!")
        return True
        
    except Exception as e:
        logger.error(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_mock_workflow()
    sys.exit(0 if success else 1)

# Made with Bob
