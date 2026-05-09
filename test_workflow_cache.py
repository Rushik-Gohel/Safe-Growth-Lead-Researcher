"""Test script to verify workflow-level caching."""

import os
import time
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set mock mode to avoid real API calls
os.environ["MOCK_SEARCH"] = "true"
os.environ["MOCK_LINKEDIN"] = "true"

from src.agent.workflow import lead_research_agent
from src.core.cache import get_cache_stats, clear_cache

def test_workflow_caching():
    """Test that workflow results are cached for identical inputs."""
    
    print("\n" + "="*80)
    print("WORKFLOW CACHING TEST")
    print("="*80)
    
    # Clear cache to start fresh
    clear_cache()
    print("\n✓ Cache cleared")
    
    # Test input
    test_input = "https://www.linkedin.com/in/test-user"
    
    print(f"\n📝 Test Input: {test_input}")
    print("\n" + "-"*80)
    
    # First run - should execute workflow
    print("\n🔄 FIRST RUN (should execute workflow):")
    print("-"*80)
    start_time = time.time()
    result1 = lead_research_agent.run(test_input)
    first_run_time = time.time() - start_time
    
    print(f"\n✓ First run completed in {first_run_time:.3f}s")
    print(f"  - Email generated: {bool(result1.get('email'))}")
    print(f"  - Errors: {len(result1.get('errors', []))}")
    
    # Check cache stats
    stats1 = get_cache_stats()
    print(f"\n📊 Cache Stats After First Run:")
    print(f"  - Hits: {stats1['hits']}")
    print(f"  - Misses: {stats1['misses']}")
    print(f"  - Size: {stats1['size']}")
    print(f"  - Hit Rate: {stats1['hit_rate']}")
    
    # Second run - should use cache
    print("\n" + "-"*80)
    print("\n🔄 SECOND RUN (should use cache):")
    print("-"*80)
    start_time = time.time()
    result2 = lead_research_agent.run(test_input)
    second_run_time = time.time() - start_time
    
    print(f"\n✓ Second run completed in {second_run_time:.3f}s")
    print(f"  - Email generated: {bool(result2.get('email'))}")
    print(f"  - Errors: {len(result2.get('errors', []))}")
    
    # Check cache stats
    stats2 = get_cache_stats()
    print(f"\n📊 Cache Stats After Second Run:")
    print(f"  - Hits: {stats2['hits']}")
    print(f"  - Misses: {stats2['misses']}")
    print(f"  - Size: {stats2['size']}")
    print(f"  - Hit Rate: {stats2['hit_rate']}")
    
    # Performance comparison
    print("\n" + "-"*80)
    print("\n⚡ PERFORMANCE COMPARISON:")
    print("-"*80)
    speedup = first_run_time / second_run_time if second_run_time > 0 else 0
    print(f"  - First run:  {first_run_time:.3f}s")
    print(f"  - Second run: {second_run_time:.3f}s")
    print(f"  - Speedup:    {speedup:.1f}x faster")
    print(f"  - Time saved: {(first_run_time - second_run_time):.3f}s")
    
    # Verify caching worked
    print("\n" + "-"*80)
    print("\n✅ VERIFICATION:")
    print("-"*80)
    
    cache_hit_increase = stats2['hits'] - stats1['hits']
    
    if cache_hit_increase > 0:
        print(f"  ✓ Cache hits increased by {cache_hit_increase}")
        print(f"  ✓ Second run was {speedup:.1f}x faster")
        print(f"  ✓ Workflow caching is WORKING! 🎉")
    else:
        print(f"  ✗ Cache hits did not increase")
        print(f"  ✗ Workflow caching may not be working properly")
    
    # Test with different input
    print("\n" + "-"*80)
    print("\n🔄 THIRD RUN (different input - should execute workflow):")
    print("-"*80)
    
    different_input = "https://www.linkedin.com/in/different-user"
    print(f"📝 Test Input: {different_input}")
    
    start_time = time.time()
    result3 = lead_research_agent.run(different_input)
    third_run_time = time.time() - start_time
    
    print(f"\n✓ Third run completed in {third_run_time:.3f}s")
    
    stats3 = get_cache_stats()
    print(f"\n📊 Final Cache Stats:")
    print(f"  - Hits: {stats3['hits']}")
    print(f"  - Misses: {stats3['misses']}")
    print(f"  - Size: {stats3['size']}")
    print(f"  - Hit Rate: {stats3['hit_rate']}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_workflow_caching()

# Made with Bob
