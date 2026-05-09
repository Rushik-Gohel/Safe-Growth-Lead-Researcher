"""Streamlit UI for Safe-Growth Lead Researcher."""

import streamlit as st
import asyncio
from typing import Optional
import sys
from pathlib import Path

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
        
        # Create placeholder for progress
        progress_placeholder = st.empty()
        result_placeholder = st.empty()
        
        with progress_placeholder.container():
            with st.spinner("🔍 Validating input..."):
                # Validate input
                validation_result = guardrails.validate_input(user_input)
                
                if not validation_result.is_safe:
                    render_error_message(
                        guardrails.get_security_response(validation_result)
                    )
                    st.stop()
        
        with progress_placeholder.container():
            with st.spinner("🔍 Researching target..."):
                try:
                    # Run agent workflow
                    result = lead_research_agent.run(user_input)
                    
                    # Clear progress
                    progress_placeholder.empty()
                    
                    # Display results
                    with result_placeholder.container():
                        # Performance metrics
                        if result.get("ttft") and result.get("total_time"):
                            render_performance_metrics(
                                ttft=result["ttft"],
                                total_time=result["total_time"]
                            )
                        
                        # Show errors if any
                        if result.get("errors"):
                            st.warning(f"⚠️ {len(result['errors'])} errors occurred during research")
                            with st.expander("View Errors"):
                                for error in result["errors"]:
                                    st.text(f"• {error}")
                        
                        # Display research summary
                        st.subheader("📋 Research Summary")
                        
                        if result.get("linkedin_profile") and result["linkedin_profile"].is_valid:
                            profile = result["linkedin_profile"]
                            st.markdown(f"""
                            **Name:** {profile.name}  
                            **Title:** {profile.title}  
                            **Company:** {profile.company}  
                            **Location:** {profile.location or 'N/A'}
                            """)
                        
                        if result.get("company_news"):
                            st.markdown(f"**Company News:** {len(result['company_news'])} articles found")
                        
                        if result.get("industry_trends"):
                            st.markdown(f"**Industry Trends:** {len(result['industry_trends'])} articles found")
                        
                        st.divider()
                        
                        # Display generated email
                        if result.get("email"):
                            render_email_output(result["email"])
                            
                            # Add download button
                            st.download_button(
                                label="📥 Download Email",
                                data=result["email"],
                                file_name="outreach_email.txt",
                                mime="text/plain"
                            )
                        else:
                            render_error_message("Failed to generate email")
                        
                        # Success message
                        render_success_message(
                            f"Research completed in {result.get('total_time', 0):.2f}s"
                        )
                
                except Exception as e:
                    progress_placeholder.empty()
                    render_error_message(f"Research failed: {str(e)}")
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
