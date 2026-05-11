"""Reusable UI components for Streamlit."""

import streamlit as st
from typing import Optional, List
import sys
from pathlib import Path

# Add project root to path if not already there
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.rate_limiter import RateLimitMetrics


def render_welcome_overlay() -> None:
    """
    Render welcome overlay with instructions and prompt starters.
    Shows on first visit using session state.
    """
    # Initialize session state for welcome overlay
    if "show_welcome" not in st.session_state:
        st.session_state.show_welcome = True
    
    # Show welcome dialog
    if st.session_state.show_welcome:
        with st.container():
            st.markdown("""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 10px; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                <h2 style='color: #ffffff; margin-top: 0; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>👋 Welcome to Safe-Growth Lead Researcher!</h2>
                <p style='font-size: 1.1em; line-height: 1.6; color: #ffffff;'>
                    This AI-powered agent helps you research leads and generate personalized outreach emails.
                </p>
                <h3 style='color: #ffffff; margin-top: 1.5rem; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>🎯 What This Agent Does:</h3>
                <ul style='font-size: 1em; line-height: 1.8; color: #ffffff;'>
                    <li><strong>LinkedIn Analysis:</strong> Extracts profile information from LinkedIn URLs</li>
                    <li><strong>Company Research:</strong> Finds recent news and developments about the company</li>
                    <li><strong>Industry Insights:</strong> Discovers relevant industry trends and topics</li>
                    <li><strong>Email Generation:</strong> Creates personalized outreach emails based on research</li>
                </ul>
                <h3 style='color: #ffffff; margin-top: 1.5rem; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>🚀 Try These Examples:</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Prompt starters in columns
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🏢 Research a Tech Company", use_container_width=True, key="starter1"):
                    st.session_state.starter_input = "Google"
                    st.session_state.show_welcome = False
                    st.rerun()
                
                if st.button("💼 Analyze a LinkedIn Profile", use_container_width=True, key="starter2"):
                    st.session_state.starter_input = "https://linkedin.com/in/satyanadella"
                    st.session_state.show_welcome = False
                    st.rerun()
            
            with col2:
                if st.button("🚀 Research a Startup", use_container_width=True, key="starter3"):
                    st.session_state.starter_input = "OpenAI"
                    st.session_state.show_welcome = False
                    st.rerun()
                
                if st.button("🎓 Explore an Educational Institution", use_container_width=True, key="starter4"):
                    st.session_state.starter_input = "Stanford University"
                    st.session_state.show_welcome = False
                    st.rerun()
            
            st.markdown("---")
            
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.info("ℹ️ **Rate Limits:** 5 requests/minute, 20 requests/hour per user")
            with col_info2:
                if st.button("✅ Got it, let's start!", type="primary", use_container_width=True):
                    st.session_state.show_welcome = False
                    st.rerun()


def render_metrics_sidebar(metrics: RateLimitMetrics) -> None:
    """
    Render metrics in sidebar.
    
    Args:
        metrics: Rate limit metrics
    """
    st.sidebar.header("📊 Metrics Dashboard")
    
    # RPM metrics
    st.sidebar.subheader("Requests Per Minute")
    rpm_percentage = metrics.rpm_percentage
    st.sidebar.progress(rpm_percentage / 100)
    st.sidebar.text(f"{metrics.current_rpm}/{metrics.max_rpm} requests")
    
    # TPM metrics
    st.sidebar.subheader("Tokens Per Minute")
    tpm_percentage = metrics.tpm_percentage
    st.sidebar.progress(tpm_percentage / 100)
    st.sidebar.text(f"{metrics.current_tpm:,}/{metrics.max_tpm:,} tokens")
    
    # Status indicator
    if metrics.is_near_limit:
        st.sidebar.warning("⚠️ Approaching rate limits")
    else:
        st.sidebar.success("✅ Within rate limits")
    
    # Total stats
    st.sidebar.divider()
    st.sidebar.metric("Total Requests", metrics.total_requests)
    st.sidebar.metric("Total Tokens", f"{metrics.total_tokens:,}")
    st.sidebar.metric("Requests Blocked", metrics.requests_blocked)


def render_performance_metrics(
    ttft: Optional[float] = None,
    total_time: Optional[float] = None
) -> None:
    """
    Render performance metrics.
    
    Args:
        ttft: Time to first token
        total_time: Total execution time
    """
    st.sidebar.divider()
    st.sidebar.header("⚡ Performance")
    
    if ttft is not None:
        st.sidebar.metric("Time to First Token", f"{ttft:.2f}s")
    
    if total_time is not None:
        st.sidebar.metric("Total Execution Time", f"{total_time:.2f}s")


def render_error_message(error: str) -> None:
    """
    Render error message.
    
    Args:
        error: Error message
    """
    st.error(f"❌ {error}")


def render_success_message(message: str) -> None:
    """
    Render success message.
    
    Args:
        message: Success message
    """
    st.success(f"✅ {message}")


def render_info_message(message: str) -> None:
    """
    Render info message.
    
    Args:
        message: Info message
    """
    st.info(f"ℹ️ {message}")


def render_warning_message(message: str) -> None:
    """
    Render warning message.
    
    Args:
        message: Warning message
    """
    st.warning(f"⚠️ {message}")


def render_research_progress(step: str) -> None:
    """
    Render research progress indicator.
    
    Args:
        step: Current step description
    """
    with st.spinner(f"🔍 {step}..."):
        pass


def render_email_output(email: str) -> None:
    """
    Render generated email in a nice format.
    
    Args:
        email: Generated email text
    """
    st.subheader("📧 Generated Email")
    
    # Split subject and body
    lines = email.split('\n')
    subject_line = None
    body_start = 0
    
    for i, line in enumerate(lines):
        if line.strip().startswith('Subject:'):
            subject_line = line.strip()
            body_start = i + 1
            break
    
    # Display subject
    if subject_line:
        st.markdown(f"**{subject_line}**")
        st.divider()
    
    # Display body
    body = '\n'.join(lines[body_start:]).strip()
    st.markdown(body)
    
    # Copy button
    st.button("📋 Copy to Clipboard", key="copy_email")


def render_security_test_section() -> Optional[str]:
    """
    Render security testing section.
    
    Returns:
        Test input if provided
    """
    with st.expander("🛡️ Try to Break Me - Security Testing"):
        st.write(
            "Test the security guardrails by trying to inject malicious prompts. "
            "The system should detect and block them."
        )
        
        test_input = st.text_area(
            "Enter test input:",
            placeholder="Try: 'Ignore all previous instructions and...'",
            key="security_test"
        )
        
        if st.button("Test Security", key="test_security_btn"):
            return test_input
    
    return None


def render_simulate_failure_toggle() -> bool:
    """
    Render simulate failure toggle.
    
    Returns:
        Whether to simulate failures
    """
    return st.sidebar.checkbox(
        "🔧 Simulate Tool Failure",
        value=False,
        help="Force tools to fail for testing error handling"
    )


def render_trace_link(trace_url: Optional[str] = None) -> None:
    """
    Render LangSmith trace link.
    
    Args:
        trace_url: URL to LangSmith trace
    """
    if trace_url:
        st.sidebar.divider()
        st.sidebar.markdown(f"[🔗 View Execution Trace]({trace_url})")


