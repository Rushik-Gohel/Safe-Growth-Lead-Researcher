"""Email generation tool using LLM."""

import logging
from typing import Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass

from ..core.config import settings
from ..core.rate_limiter import token_governor

logger = logging.getLogger(__name__)


@dataclass
class EmailContext:
    """Context for email generation."""
    
    target_name: Optional[str] = None
    target_title: Optional[str] = None
    target_company: Optional[str] = None
    target_bio: Optional[str] = None
    company_news: Optional[str] = None
    industry_trends: Optional[str] = None
    linkedin_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "target_name": self.target_name,
            "target_title": self.target_title,
            "target_company": self.target_company,
            "target_bio": self.target_bio,
            "company_news": self.company_news,
            "industry_trends": self.industry_trends,
            "linkedin_url": self.linkedin_url,
        }


class EmailGenerator:
    """
    Email generator using Google Gemini with streaming support.
    """
    
    def __init__(self):
        """Initialize email generator."""
        self.model_name = settings.model_name
        self.temperature = settings.temperature
        self.max_tokens = settings.max_output_tokens
        
        # Initialize Gemini
        self._setup_gemini()
        
        logger.info(
            f"EmailGenerator initialized: model={self.model_name}, "
            f"temp={self.temperature}"
        )
    
    def _setup_gemini(self) -> None:
        """Setup Google Gemini client."""
        try:
            from google import genai
            from google.genai import types
            
            # Initialize client
            client = genai.Client(api_key=settings.google_api_key)
            
            # Store client and config
            self.client = client
            self.generation_config = types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            )
            
            logger.info("Gemini client initialized")
            
        except ImportError:
            logger.error("google-genai library not installed. Install with: pip install google-genai")
            self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {str(e)}")
            self.client = None
    
    def _build_prompt(self, context: EmailContext) -> str:
        """
        Build email generation prompt from context.
        
        Args:
            context: Email context
            
        Returns:
            Formatted prompt
        """
        prompt_parts = [
            "You are a professional sales development representative writing a personalized outreach email.",
            "Your goal is to create a compelling, concise email that demonstrates genuine research and value.",
            "",
            "## Target Information:",
        ]
        
        if context.target_name:
            prompt_parts.append(f"- Name: {context.target_name}")
        if context.target_title:
            prompt_parts.append(f"- Title: {context.target_title}")
        if context.target_company:
            prompt_parts.append(f"- Company: {context.target_company}")
        if context.target_bio:
            prompt_parts.append(f"- Bio: {context.target_bio}")
        
        if context.company_news:
            prompt_parts.extend([
                "",
                "## Recent Company News:",
                context.company_news
            ])
        
        if context.industry_trends:
            prompt_parts.extend([
                "",
                "## Industry Trends:",
                context.industry_trends
            ])
        
        prompt_parts.extend([
            "",
            "## Instructions:",
            "1. Write a personalized cold outreach email (150-200 words)",
            "2. Reference specific details from the research above",
            "3. Demonstrate understanding of their role and company",
            "4. Offer clear value proposition",
            "5. Include a soft call-to-action",
            "6. Use professional but conversational tone",
            "7. Do NOT use generic templates or buzzwords",
            "",
            "## Email Format:",
            "Subject: [Compelling subject line]",
            "",
            "[Email body]",
            "",
            "Best regards,",
            "[Your name]",
            "",
            "Generate the email now:"
        ])
        
        return "\n".join(prompt_parts)
    
    def generate_email(self, context: EmailContext) -> str:
        """
        Generate email synchronously.
        
        Args:
            context: Email context
            
        Returns:
            Generated email text
        """
        if not self.client:
            raise RuntimeError("Gemini client not initialized")
        
        # Build prompt
        prompt = self._build_prompt(context)
        
        # Check rate limits
        estimated_tokens = len(prompt.split()) * 2  # Rough estimate
        token_governor.wait_if_needed(estimated_tokens)
        
        try:
            logger.info("Generating email...")
            
            # Generate response using new API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=self.generation_config
            )
            
            # Extract text
            email_text = response.text
            
            # Record token usage (estimate for now)
            token_governor.record_request(estimated_tokens)
            logger.info(f"Email generated: ~{estimated_tokens} tokens used")
            
            return email_text
            
        except Exception as e:
            logger.error(f"Email generation failed: {str(e)}")
            raise
    
    async def generate_email_stream(
        self,
        context: EmailContext
    ) -> AsyncIterator[str]:
        """
        Generate email with streaming.
        
        Args:
            context: Email context
            
        Yields:
            Email text chunks
        """
        if not self.client:
            raise RuntimeError("Gemini client not initialized")
        
        # Build prompt
        prompt = self._build_prompt(context)
        
        # Check rate limits
        estimated_tokens = len(prompt.split()) * 2
        token_governor.wait_if_needed(estimated_tokens)
        
        try:
            logger.info("Generating email (streaming)...")
            
            # Generate streaming response using new API
            response = self.client.models.generate_content_stream(
                model=self.model_name,
                contents=prompt,
                config=self.generation_config
            )
            
            total_tokens = 0
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
                    # Rough token estimation
                    total_tokens += len(chunk.text.split())
            
            # Record token usage
            token_governor.record_request(total_tokens)
            logger.info(f"Email generated (streaming): ~{total_tokens} tokens used")
            
        except Exception as e:
            logger.error(f"Streaming email generation failed: {str(e)}")
            raise
    
    def validate_email(self, email_text: str) -> bool:
        """
        Validate generated email.
        
        Args:
            email_text: Generated email
            
        Returns:
            True if valid
        """
        # Basic validation
        if not email_text or len(email_text) < 50:
            return False
        
        # Check for subject line
        if "Subject:" not in email_text:
            return False
        
        # Check for greeting
        common_greetings = ["Hi", "Hello", "Dear", "Hey"]
        has_greeting = any(greeting in email_text for greeting in common_greetings)
        
        return has_greeting


# Global email generator instance
email_generator = EmailGenerator()

# Made with Bob
