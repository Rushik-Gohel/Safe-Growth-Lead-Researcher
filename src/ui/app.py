"""Streamlit UI for Safe-Growth Lead Researcher."""

import streamlit as st
import asyncio
from typing import Optional
import sys
import logging
from pathlib import Path

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
from src.security.guardrails import guardrails
from src.ui.components import (
    render_metrics_sidebar,
    render_performance_metrics,
    render_error_message,
    render_success_message,
    render_email_output,
    render_security_test_section,
    render_simulate_failure_toggle,
    render_trace_link
)


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
    
    # Sidebar metrics
    metrics = token_governor.get_metrics()
    render_metrics_sidebar(metrics)
    
    # Simulate failure toggle
    simulate_failure = render_simulate_failure_toggle()
    
    # Main input area
    st.header("Research Target")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        user_input = st.text_input(
            "Enter LinkedIn URL or Company Name:",
            placeholder="https://linkedin.com/in/john-doe or Acme Corporation",
            help="Provide a LinkedIn profile URL or company name to research"
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        research_button = st.button("🚀 Start Research", type="primary", use_container_width=True)
    
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
        
        # Validate input first
        validation_result = guardrails.validate_input(user_input)
        
        if not validation_result.is_safe:
            render_error_message(
                guardrails.get_security_response(validation_result)
            )
            st.stop()
        
        estimated_tokens = max(250, min(1000, len(user_input) * 4))
        can_proceed, wait_time = token_governor.check_rate_limit(
            estimated_tokens=estimated_tokens
        )
        
        if not can_proceed:
            render_error_message(
                f"Rate limit reached for research input. Please wait {wait_time:.1f} seconds before trying again."
            )
            st.stop()
        
        # Run workflow with spinner
        result = None
        with st.spinner("🔍 Researching target..."):
            try:
                # Run agent workflow
                result = lead_research_agent.run(user_input)
                token_governor.record_request(tokens_used=estimated_tokens)
                
                logger.info(f"Workflow result received: {type(result)}")
                logger.info(f"Result keys: {result.keys() if result else 'None'}")
                
                # Check if we got a valid result
                if not result:
                    st.error("No result returned from agent")
                    st.stop()
                
            except Exception as e:
                logger.error(f"Workflow failed: {str(e)}", exc_info=True)
                st.error(f"❌ Research failed: {str(e)}")
                with st.expander("Error Details"):
                    st.exception(e)
                st.stop()
        
        # Display results AFTER spinner completes (only if result exists)
        if result:
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
                if profile and hasattr(profile, 'is_valid') and profile.is_valid:
                    st.markdown(f"""
                    **Name:** {getattr(profile, 'name', 'N/A')}
                    **Title:** {getattr(profile, 'title', 'N/A')}
                    **Company:** {getattr(profile, 'company', 'N/A')}
                    **Location:** {getattr(profile, 'location', None) or 'N/A'}
                    """)
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

# Made with Bob
