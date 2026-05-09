"""Test workflow without LinkedIn profile data."""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Import after path setup
from src.agent.workflow import lead_research_agent

def test_company_research():
    """Test research with just a company name (no LinkedIn)."""
    logger.info("=" * 80)
    logger.info("Testing workflow with company name only (no LinkedIn profile)")
    logger.info("=" * 80)
    
    # Test with a well-known company
    company_name = "Microsoft"
    
    logger.info(f"\nResearching: {company_name}")
    logger.info("-" * 80)
    
    try:
        result = lead_research_agent.run(company_name)
        
        logger.info("\n" + "=" * 80)
        logger.info("RESULTS:")
        logger.info("=" * 80)
        
        # Check results
        logger.info(f"\n✓ Validation: {'Passed' if result.get('is_valid') else 'Failed'}")
        logger.info(f"✓ LinkedIn Profile: {'Available' if result.get('linkedin_profile') and result['linkedin_profile'].is_valid else 'Not Available (Expected)'}")
        logger.info(f"✓ Company News: {len(result.get('company_news', []))} articles")
        logger.info(f"✓ Industry Trends: {len(result.get('industry_trends', []))} articles")
        logger.info(f"✓ Email Generated: {'Yes' if result.get('email') else 'No'}")
        logger.info(f"✓ Errors: {len(result.get('errors', []))}")
        logger.info(f"✓ Total Time: {result.get('total_time', 0):.2f}s")
        
        if result.get('errors'):
            logger.info("\nErrors encountered:")
            for error in result['errors']:
                logger.info(f"  - {error}")
        
        if result.get('email'):
            logger.info("\n" + "=" * 80)
            logger.info("GENERATED EMAIL:")
            logger.info("=" * 80)
            logger.info(result['email'])
            logger.info("=" * 80)
        
        # Verify workflow completed successfully
        assert result.get('is_valid'), "Input validation failed"
        assert result.get('email'), "Email generation failed"
        assert result.get('company_news'), "Company news search failed"
        
        logger.info("\n✅ TEST PASSED: Workflow completed successfully without LinkedIn profile!")
        return True
        
    except Exception as e:
        logger.error(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_company_research()
    sys.exit(0 if success else 1)

# Made with Bob
