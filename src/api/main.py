"""FastAPI backend for Safe-Growth Lead Researcher."""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

from ..agent.workflow import lead_research_agent
from ..core.rate_limiter import token_governor
from ..security.guardrails import guardrails
from ..core.config import settings

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Safe-Growth Lead Researcher API",
    description="AI-powered lead research and email generation API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ResearchRequest(BaseModel):
    """Research request model."""
    
    input: str = Field(
        ...,
        description="LinkedIn URL or company name to research",
        min_length=1,
        max_length=1000
    )
    simulate_failure: bool = Field(
        default=False,
        description="Simulate tool failures for testing"
    )


class ResearchResponse(BaseModel):
    """Research response model."""
    
    success: bool
    email: Optional[str] = None
    linkedin_profile: Optional[Dict[str, Any]] = None
    company_news_count: int = 0
    industry_trends_count: int = 0
    errors: List[str] = []
    metrics: Dict[str, Any] = {}


class ValidationRequest(BaseModel):
    """Validation request model."""
    
    input: str = Field(..., description="Input to validate")


class ValidationResponse(BaseModel):
    """Validation response model."""
    
    is_safe: bool
    reason: Optional[str] = None
    threat_level: str
    detected_patterns: List[str] = []


class MetricsResponse(BaseModel):
    """Metrics response model."""
    
    current_rpm: int
    current_tpm: int
    max_rpm: int
    max_tpm: int
    rpm_percentage: float
    tpm_percentage: float
    total_requests: int
    total_tokens: int
    requests_blocked: int
    is_near_limit: bool


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    version: str
    gemini_configured: bool
    tavily_configured: bool


# Endpoints
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "Safe-Growth Lead Researcher API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        gemini_configured=bool(settings.google_api_key),
        tavily_configured=bool(settings.tavily_api_key)
    )


@app.get("/metrics", response_model=MetricsResponse, tags=["Metrics"])
async def get_metrics():
    """Get current rate limiting metrics."""
    metrics = token_governor.get_metrics()
    
    return MetricsResponse(
        current_rpm=metrics.current_rpm,
        current_tpm=metrics.current_tpm,
        max_rpm=metrics.max_rpm,
        max_tpm=metrics.max_tpm,
        rpm_percentage=metrics.rpm_percentage,
        tpm_percentage=metrics.tpm_percentage,
        total_requests=metrics.total_requests,
        total_tokens=metrics.total_tokens,
        requests_blocked=metrics.requests_blocked,
        is_near_limit=metrics.is_near_limit
    )


@app.post("/validate", response_model=ValidationResponse, tags=["Security"])
async def validate_input(request: ValidationRequest):
    """Validate input for security threats."""
    validation_result = guardrails.validate_input(request.input)
    
    return ValidationResponse(
        is_safe=validation_result.is_safe,
        reason=validation_result.reason,
        threat_level=validation_result.threat_level,
        detected_patterns=validation_result.detected_patterns
    )


@app.post("/research", response_model=ResearchResponse, tags=["Research"])
async def research_lead(request: ResearchRequest):
    """
    Research a lead and generate personalized email.
    
    This endpoint:
    1. Validates input for security threats
    2. Scrapes LinkedIn profile (if URL provided)
    3. Searches for company news and industry trends
    4. Generates personalized outreach email
    """
    try:
        # Validate input
        validation_result = guardrails.validate_input(request.input)
        
        if not validation_result.is_safe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Security validation failed",
                    "reason": validation_result.reason,
                    "threat_level": validation_result.threat_level
                }
            )
        
        # Run agent workflow
        logger.info(f"Starting research for: {request.input[:50]}...")
        result = lead_research_agent.run(request.input)
        
        # Build response
        response = ResearchResponse(
            success=result.get("email") is not None,
            email=result.get("email"),
            errors=result.get("errors", []),
            metrics={
                "ttft": result.get("ttft"),
                "total_time": result.get("total_time"),
                "start_time": result.get("start_time"),
                "end_time": result.get("end_time")
            }
        )
        
        # Add LinkedIn profile if available
        if result.get("linkedin_profile") and result["linkedin_profile"].is_valid:
            response.linkedin_profile = result["linkedin_profile"].to_dict()
        
        # Add counts
        if result.get("company_news"):
            response.company_news_count = len(result["company_news"])
        
        if result.get("industry_trends"):
            response.industry_trends_count = len(result["industry_trends"])
        
        logger.info(
            f"Research completed: success={response.success}, "
            f"errors={len(response.errors)}"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Research failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research failed: {str(e)}"
        )


@app.post("/reset-metrics", tags=["Metrics"])
async def reset_metrics():
    """Reset rate limiting metrics (for testing)."""
    token_governor.reset()
    return {"message": "Metrics reset successfully"}


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return {
        "error": exc.detail,
        "status_code": exc.status_code
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return {
        "error": "Internal server error",
        "detail": str(exc),
        "status_code": 500
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

# Made with Bob
