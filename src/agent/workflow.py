"""LangGraph agent workflow for lead research."""

import logging
from typing import TypedDict, Annotated, Sequence, Optional
from operator import add
import time

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from ..core.config import settings
from ..core.cache import cached
from ..security.guardrails import guardrails
from ..tools.linkedin_scraper import linkedin_scraper, LinkedInProfile
from ..tools.search_tools import search_tools, SearchResult
from ..tools.email_generator import email_generator, EmailContext

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for the agent workflow."""
    
    # Input
    user_input: str
    
    # Validation
    is_valid: bool
    validation_error: Optional[str]
    
    # Research data
    linkedin_profile: Optional[LinkedInProfile]
    company_news: Optional[list[SearchResult]]
    industry_trends: Optional[list[SearchResult]]
    
    # Generated output
    email: Optional[str]
    
    # Metadata
    messages: Annotated[Sequence[BaseMessage], add]
    errors: list[str]
    start_time: float
    end_time: Optional[float]
    
    # Metrics
    ttft: Optional[float]  # Time to first token
    total_time: Optional[float]


class LeadResearchAgent:
    """
    LangGraph agent for lead research and email generation.
    Implements the state machine defined in ARCHITECTURE.md.
    """
    
    def __init__(self):
        """Initialize the agent workflow."""
        self.graph = self._build_graph()
        logger.info("LeadResearchAgent initialized")
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("validate_input", self._validate_input)
        workflow.add_node("extract_target", self._extract_target)
        workflow.add_node("scrape_linkedin", self._scrape_linkedin)
        workflow.add_node("search_company_news", self._search_company_news)
        workflow.add_node("search_industry_trends", self._search_industry_trends)
        workflow.add_node("aggregate_data", self._aggregate_data)
        workflow.add_node("generate_email", self._generate_email)
        workflow.add_node("handle_error", self._handle_error)
        
        # Set entry point
        workflow.set_entry_point("validate_input")
        
        # Add edges
        workflow.add_conditional_edges(
            "validate_input",
            self._should_continue_after_validation,
            {
                "continue": "extract_target",
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("extract_target", "scrape_linkedin")
        workflow.add_edge("scrape_linkedin", "search_company_news")
        workflow.add_edge("search_company_news", "search_industry_trends")
        workflow.add_edge("search_industry_trends", "aggregate_data")
        workflow.add_edge("aggregate_data", "generate_email")
        workflow.add_edge("generate_email", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    def _validate_input(self, state: AgentState) -> AgentState:
        """Validate user input using security guardrails."""
        logger.info("Validating input...")
        
        user_input = state["user_input"]
        
        # Validate with guardrails
        is_safe, sanitized, error = guardrails.validate_and_sanitize(user_input)
        
        if not is_safe:
            logger.warning(f"Input validation failed: {error}")
            state["is_valid"] = False
            state["validation_error"] = error
            state["errors"].append(f"Validation: {error}")
        else:
            logger.info("Input validated successfully")
            state["is_valid"] = True
            state["user_input"] = sanitized
            state["messages"].append(
                HumanMessage(content=f"Research request: {sanitized}")
            )
        
        return state
    
    def _should_continue_after_validation(self, state: AgentState) -> str:
        """Determine next step after validation."""
        return "continue" if state["is_valid"] else "error"
    
    def _extract_target(self, state: AgentState) -> AgentState:
        """Extract target information from input."""
        logger.info("Extracting target information...")
        
        user_input = state["user_input"]
        
        # Check if input contains LinkedIn URL
        linkedin_url = linkedin_scraper.extract_profile_from_text(user_input)
        
        if linkedin_url:
            logger.info(f"LinkedIn URL detected: {linkedin_url}")
            state["user_input"] = linkedin_url
        else:
            logger.info("No LinkedIn URL detected, treating as company/person name")
        
        state["messages"].append(
            AIMessage(content=f"Target identified: {user_input}")
        )
        
        return state
    
    def _scrape_linkedin(self, state: AgentState) -> AgentState:
        """Scrape LinkedIn profile if URL provided (optional - continues on failure)."""
        logger.info("Scraping LinkedIn profile...")
        
        user_input = state["user_input"]
        
        # Check if it's a LinkedIn URL
        if "linkedin.com/in/" in user_input:
            try:
                profile = linkedin_scraper.scrape_profile(user_input)
                state["linkedin_profile"] = profile
                
                if profile.is_valid:
                    logger.info(f"LinkedIn profile scraped: {profile.name}")
                    state["messages"].append(
                        AIMessage(content=f"Found LinkedIn profile: {profile.name}")
                    )
                else:
                    error_msg = profile.error or "Unknown error - profile data not available"
                    logger.warning(f"LinkedIn scraping failed: {error_msg}")
                    logger.info("Continuing research without LinkedIn profile data...")
                    state["errors"].append(f"LinkedIn: {error_msg} (continuing without profile)")
                    state["messages"].append(
                        AIMessage(content="LinkedIn profile unavailable - continuing with company research")
                    )
                    
            except Exception as e:
                logger.error(f"LinkedIn scraping error: {str(e)}")
                logger.info("Continuing research without LinkedIn profile data...")
                state["errors"].append(f"LinkedIn: {str(e)} (continuing without profile)")
                state["messages"].append(
                    AIMessage(content="LinkedIn profile unavailable - continuing with company research")
                )
        else:
            logger.info("No LinkedIn URL provided, using input as company/person name")
            state["messages"].append(
                AIMessage(content=f"Researching: {user_input}")
            )
        
        return state
    
    def _search_company_news(self, state: AgentState) -> AgentState:
        """Search for company news."""
        logger.info("Searching for company news...")
        
        # Determine company name
        company_name = None
        if state.get("linkedin_profile") and state["linkedin_profile"].company:
            company_name = state["linkedin_profile"].company
        else:
            # Use user input as company name
            company_name = state["user_input"]
        
        if company_name:
            try:
                results = search_tools.search_company_news(company_name, max_results=5)
                state["company_news"] = results
                logger.info(f"Found {len(results)} company news articles")
                state["messages"].append(
                    AIMessage(content=f"Found {len(results)} recent news articles")
                )
            except Exception as e:
                logger.error(f"Company news search failed: {str(e)}")
                state["errors"].append(f"News search: {str(e)}")
        
        return state
    
    def _search_industry_trends(self, state: AgentState) -> AgentState:
        """Search for industry trends."""
        logger.info("Searching for industry trends...")
        
        # Determine industry from profile or input
        industry = None
        if state.get("linkedin_profile") and state["linkedin_profile"].title:
            # Extract industry from title (simplified)
            title = state["linkedin_profile"].title.lower()
            if "software" in title or "tech" in title:
                industry = "technology"
            elif "sales" in title or "marketing" in title:
                industry = "sales and marketing"
            elif "finance" in title:
                industry = "finance"
        
        if not industry:
            industry = "business"  # Default
        
        try:
            results = search_tools.search_industry_trends(industry, max_results=3)
            state["industry_trends"] = results
            logger.info(f"Found {len(results)} industry trend articles")
            state["messages"].append(
                AIMessage(content=f"Found {len(results)} industry trends")
            )
        except Exception as e:
            logger.error(f"Industry trends search failed: {str(e)}")
            state["errors"].append(f"Trends search: {str(e)}")
        
        return state
    
    def _aggregate_data(self, state: AgentState) -> AgentState:
        """Aggregate all research data."""
        logger.info("Aggregating research data...")
        
        # Build summary message
        summary_parts = ["Research completed:"]
        
        if state.get("linkedin_profile") and state["linkedin_profile"].is_valid:
            profile = state["linkedin_profile"]
            summary_parts.append(
                f"- Profile: {profile.name} ({profile.title} at {profile.company})"
            )
        
        if state.get("company_news"):
            summary_parts.append(f"- Company news: {len(state['company_news'])} articles")
        
        if state.get("industry_trends"):
            summary_parts.append(f"- Industry trends: {len(state['industry_trends'])} articles")
        
        if state.get("errors"):
            summary_parts.append(f"- Errors encountered: {len(state['errors'])}")
        
        state["messages"].append(
            AIMessage(content="\n".join(summary_parts))
        )
        
        return state
    
    def _generate_email(self, state: AgentState) -> AgentState:
        """Generate personalized email."""
        logger.info("Generating email...")
        
        # Record TTFT
        if not state.get("ttft"):
            state["ttft"] = time.time() - state["start_time"]
        
        # Build email context
        context = EmailContext()
        
        if state.get("linkedin_profile") and state["linkedin_profile"].is_valid:
            profile = state["linkedin_profile"]
            context.target_name = profile.name
            context.target_title = profile.title
            context.target_company = profile.company
            context.target_bio = profile.bio
            context.linkedin_url = profile.url
        
        if state.get("company_news"):
            context.company_news = search_tools.format_results_for_llm(
                state["company_news"]
            )
        
        if state.get("industry_trends"):
            context.industry_trends = search_tools.format_results_for_llm(
                state["industry_trends"]
            )
        
        try:
            email = email_generator.generate_email(context)
            state["email"] = email
            logger.info("Email generated successfully")
            state["messages"].append(
                AIMessage(content="Email draft completed")
            )
        except Exception as e:
            logger.error(f"Email generation failed: {str(e)}")
            state["errors"].append(f"Email generation: {str(e)}")
            state["email"] = "Error: Failed to generate email"
        
        # Record end time
        state["end_time"] = time.time()
        state["total_time"] = state["end_time"] - state["start_time"]
        
        return state
    
    def _handle_error(self, state: AgentState) -> AgentState:
        """Handle validation or critical errors."""
        logger.error("Handling error state")
        
        error_message = state.get("validation_error", "Unknown error")
        state["messages"].append(
            AIMessage(content=f"Error: {error_message}")
        )
        
        state["end_time"] = time.time()
        state["total_time"] = state["end_time"] - state["start_time"]
        
        return state
    
    @cached(ttl=settings.workflow_cache_ttl, key_prefix="workflow")
    def _run_workflow_cached(self, user_input: str) -> AgentState:
        """
        Internal cached method for workflow execution.
        
        Args:
            user_input: User's research request
            
        Returns:
            Final agent state
        """
        logger.info(f"Executing workflow (cache miss) for: {user_input[:50]}...")
        
        # Initialize state
        initial_state: AgentState = {
            "user_input": user_input,
            "is_valid": False,
            "validation_error": None,
            "linkedin_profile": None,
            "company_news": None,
            "industry_trends": None,
            "email": None,
            "messages": [],
            "errors": [],
            "start_time": time.time(),
            "end_time": None,
            "ttft": None,
            "total_time": None,
        }
        
        # Run workflow
        final_state = self.graph.invoke(initial_state)
        
        logger.info(
            f"Workflow completed in {final_state.get('total_time', 0):.2f}s "
            f"with {len(final_state.get('errors', []))} errors"
        )
        
        return final_state
    
    def run(self, user_input: str) -> AgentState:
        """
        Run the agent workflow with caching.
        
        If the same input has been processed recently (within cache TTL),
        returns the cached result instead of re-running the entire workflow.
        
        Args:
            user_input: User's research request
            
        Returns:
            Final agent state (from cache or fresh execution)
        """
        logger.info(f"Starting agent workflow for: {user_input[:50]}...")
        
        # Use cached workflow execution
        return self._run_workflow_cached(user_input)


# Global agent instance
lead_research_agent = LeadResearchAgent()

# Made with Bob
