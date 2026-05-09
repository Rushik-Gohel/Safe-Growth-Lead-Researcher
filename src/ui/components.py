"""Reusable UI components for Streamlit."""

import streamlit as st
from typing import Optional
from ..core.rate_limiter import RateLimitMetrics


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

# Made with Bob
