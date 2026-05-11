"""Streamlit UI for Safe-Growth Lead Researcher."""

import streamlit as st
import asyncio
from typing import Optional
import sys
import logging
from pathlib import Path
import os
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Add project root to path if not already there
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.agent.workflow import lead_research_agent
from src.core.rate_limiter import token_governor
from src.core.user_rate_limiter import user_rate_limiter
from src.security.guardrails import guardrails
from src.ui.components import (
    render_metrics_sidebar,
    render_performance_metrics,
    render_error_message,
    render_success_message,
    render_email_output,
    render_security_test_section,
    render_simulate_failure_toggle,
    render_trace_link,
    render_welcome_overlay
)

# Get API base URL from environment (for Render deployment)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def call_research_api(user_input: str, simulate_failure: bool = False) -> dict:
    """Call the research API endpoint."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/research",
            json={
                "input": user_input,
                "simulate_failure": simulate_failure
            },
            timeout=120  # 2 minute timeout for research
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        raise Exception("Request timed out. Please try again.")
    except requests.exceptions.ConnectionError:
        raise Exception(f"Could not connect to API at {API_BASE_URL}")
    except requests.exceptions.HTTPError as e:
        error_detail = e.response.json() if e.response.content else str(e)
        raise Exception(f"API error: {error_detail}")
    except Exception as e:
        raise Exception(f"Unexpected error: {str(e)}")


# Page configuration
st.set_page_config(
    page_title="Safe-Growth Lead Researcher",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main():
    """Main Streamlit application."""
    
    # Title and description
    st.title("🔍 Safe-Growth Lead Researcher")
    st.markdown(
        "AI-powered lead research agent that analyzes LinkedIn profiles, "
        "finds recent news, and drafts personalized outreach emails."
    )
    
    # Show welcome overlay on first visit
    render_welcome_overlay()
    
    # Sidebar metrics
    metrics = token_governor.get_metrics()
    render_metrics_sidebar(metrics)
    
    # Get user session ID for rate limiting
    if "user_session_id" not in st.session_state:
        import uuid
        st.session_state.user_session_id = str(uuid.uuid4())
    
    user_id = st.session_state.user_session_id
    
    # Display user rate limit info in sidebar
    user_stats = user_rate_limiter.get_user_stats(user_id)
    st.sidebar.divider()
    st.sidebar.subheader("👤 Your Usage")
    st.sidebar.text(f"This minute: {user_stats['requests_this_minute']}/{user_stats['minute_limit']}")
    st.sidebar.text(f"This hour: {user_stats['requests_this_hour']}/{user_stats['hour_limit']}")
    
    # Simulate failure toggle
    simulate_failure = render_simulate_failure_toggle()
    
    # Main input area
    st.header("Research Target")
    
    # Check if we have a starter input from welcome overlay and set it
    if "starter_input" in st.session_state and "research_input" not in st.session_state:
        st.session_state.research_input = st.session_state.starter_input
        st.session_state.pop("starter_input")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        user_input = st.text_input(
            "Enter LinkedIn URL or Company Name:",
            placeholder="https://linkedin.com/in/john-doe or Acme Corporation",
            help="Provide a LinkedIn profile URL or company name to research",
            key="research_input"
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        col2a, col2b = st.columns(2)
        with col2a:
            research_button = st.button("🚀 Start Research", type="primary", use_container_width=True)
        with col2b:
            if "research_result" in st.session_state:
                if st.button("🔄 New Search", use_container_width=True):
                    # Clear previous results
                    st.session_state.pop("research_result", None)
                    st.session_state.pop("clipboard_content", None)
                    st.rerun()
    
    # Security testing section
    security_test_input = render_security_test_section()
    
    # Handle security test
    if security_test_input:
        st.subheader("🛡️ Security Test Results")
        validation_result = guardrails.validate_input(security_test_input)
        
        if validation_result.is_safe:
            render_success_message("Input passed security validation")
        else:
            render_error_message(
                f"Security threat detected: {validation_result.reason}\n"
                f"Threat level: {validation_result.threat_level.upper()}"
            )
            st.json({
                "detected_patterns": validation_result.detected_patterns,
                "threat_level": validation_result.threat_level
            })
    
    # Handle research request
    if research_button and user_input:
        st.divider()
        
        # Check user rate limit first
        can_proceed_user, user_error = user_rate_limiter.check_rate_limit(user_id)
        if not can_proceed_user:
            render_error_message(user_error or "Rate limit exceeded")
            st.stop()
        
        # Validate input
        validation_result = guardrails.validate_input(user_input)
        
        if not validation_result.is_safe:
            render_error_message(
                guardrails.get_security_response(validation_result)
            )
            st.stop()
        
        # Check global rate limit
        estimated_tokens = max(250, min(1000, len(user_input) * 4))
        can_proceed, wait_time = token_governor.check_rate_limit(
            estimated_tokens=estimated_tokens
        )
        
        if not can_proceed:
            render_error_message(
                f"Rate limit reached for research input. Please wait {wait_time:.1f} seconds before trying again."
            )
            st.stop()
        
        # Record user request
        user_rate_limiter.record_request(user_id)
        
        # Run workflow with spinner
        result = None
        with st.spinner("🔍 Researching target..."):
            try:
                # Check if API_BASE_URL is set (Render deployment mode)
                if API_BASE_URL != "http://localhost:8000":
                    # Call API endpoint
                    logger.info(f"Calling API at {API_BASE_URL}")
                    api_response = call_research_api(user_input, simulate_failure)
                    
                    # Convert API response to workflow result format
                    result = {
                        "email": api_response.get("email"),
                        "linkedin_profile": api_response.get("linkedin_profile"),
                        "company_news": [],  # API doesn't return full data
                        "industry_trends": [],  # API doesn't return full data
                        "errors": api_response.get("errors", []),
                        "ttft": api_response.get("metrics", {}).get("ttft"),
                        "total_time": api_response.get("metrics", {}).get("total_time"),
                    }
                    
                    # Add counts from API response
                    if api_response.get("company_news_count"):
                        result["company_news"] = [None] * api_response["company_news_count"]
                    if api_response.get("industry_trends_count"):
                        result["industry_trends"] = [None] * api_response["industry_trends_count"]
                    
                else:
                    # Local mode - run agent workflow directly
                    logger.info("Running agent workflow locally")
                    result = lead_research_agent.run(user_input)
                    token_governor.record_request(tokens_used=estimated_tokens)
                
                logger.info(f"Workflow result received: {type(result)}")
                logger.info(f"Result keys: {result.keys() if result else 'None'}")
                
                # Check if we got a valid result
                if not result:
                    st.error("No result returned from agent")
                    st.stop()
                
                # Store result in session state to persist across reruns
                st.session_state.research_result = result
                
            except Exception as e:
                logger.error(f"Workflow failed: {str(e)}", exc_info=True)
                st.error(f"❌ Research failed: {str(e)}")
                with st.expander("Error Details"):
                    st.exception(e)
                st.stop()
    
    # Display results from session state (persists across reruns)
    if "research_result" in st.session_state:
        result = st.session_state.research_result
        if result:
            st.divider()
            try:
                # Performance metrics
                if result.get("ttft") and result.get("total_time"):
                    render_performance_metrics(
                        ttft=result["ttft"],
                        total_time=result["total_time"]
                    )
                
                # Show errors if any
                if result.get("errors") and len(result["errors"]) > 0:
                    st.warning(f"⚠️ {len(result['errors'])} errors occurred during research")
                    with st.expander("View Errors"):
                        for error in result["errors"]:
                            st.text(f"• {error}")
                
                # Display research summary
                st.subheader("📋 Research Summary")
                
                # LinkedIn profile (with null checks)
                profile = result.get("linkedin_profile")
                if profile:
                    # Handle both dict (from API) and object (from local workflow)
                    if isinstance(profile, dict):
                        if profile.get("is_valid"):
                            st.markdown(f"""
                            **Name:** {profile.get('name', 'N/A')}
                            **Title:** {profile.get('title', 'N/A')}
                            **Company:** {profile.get('company', 'N/A')}
                            **Location:** {profile.get('location') or 'N/A'}
                            """)
                        else:
                            st.info("ℹ️ LinkedIn profile data not available - research based on company information")
                    elif hasattr(profile, 'is_valid') and profile.is_valid:
                        st.markdown(f"""
                        **Name:** {getattr(profile, 'name', 'N/A')}
                        **Title:** {getattr(profile, 'title', 'N/A')}
                        **Company:** {getattr(profile, 'company', 'N/A')}
                        **Location:** {getattr(profile, 'location', None) or 'N/A'}
                        """)
                    else:
                        st.info("ℹ️ LinkedIn profile data not available - research based on company information")
                else:
                    st.info("ℹ️ LinkedIn profile data not available - research based on company information")
                
                # Company news (with null checks)
                company_news = result.get("company_news") or []
                if len(company_news) > 0:
                    st.markdown(f"**Company News:** {len(company_news)} articles found")
                else:
                    st.info("No company news found")
                
                # Industry trends (with null checks)
                industry_trends = result.get("industry_trends") or []
                if len(industry_trends) > 0:
                    st.markdown(f"**Industry Trends:** {len(industry_trends)} articles found")
                else:
                    st.info("No industry trends found")
                
                st.divider()
                
                # Display generated email
                email = result.get("email")
                if email and email.strip():
                    render_email_output(email)
                    
                    # Add download button
                    st.download_button(
                        label="📥 Download Email",
                        data=email,
                        file_name="outreach_email.txt",
                        mime="text/plain"
                    )
                    
                    # Success message
                    render_success_message(
                        f"✅ Research completed in {result.get('total_time', 0):.2f}s"
                    )
                else:
                    render_error_message("Failed to generate email. Please check the errors above.")
                    logger.error(f"Email generation failed. Result: {result}")
                    
            except Exception as e:
                logger.error(f"Error displaying results: {str(e)}", exc_info=True)
                st.error(f"❌ Error displaying results: {str(e)}")
                with st.expander("Error Details"):
                    st.exception(e)
    
    elif research_button and not user_input:
        render_error_message("Please enter a LinkedIn URL or company name")
    
    # Footer
    st.divider()
    st.markdown(
        """
        <div style='text-align: center; color: gray; font-size: 0.8em;'>
        Built with LangGraph, Google Gemini, and Streamlit | 
        <a href='https://github.com/yourusername/safe-growth-researcher' target='_blank'>GitHub</a>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()


