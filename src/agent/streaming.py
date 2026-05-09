"""Streaming architecture for real-time email generation."""

import logging
import time
from typing import AsyncIterator, Dict, Any
from dataclasses import dataclass

from ..tools.email_generator import EmailContext, email_generator

logger = logging.getLogger(__name__)


@dataclass
class StreamMetrics:
    """Metrics for streaming operations."""
    
    ttft: float  # Time to first token
    total_time: float
    tokens_generated: int
    chunks_received: int


class StreamingEmailGenerator:
    """
    Streaming wrapper for email generation with metrics tracking.
    """
    
    def __init__(self):
        """Initialize streaming generator."""
        self.generator = email_generator
        logger.info("StreamingEmailGenerator initialized")
    
    async def generate_stream(
        self,
        context: EmailContext
    ) -> AsyncIterator[tuple[str, StreamMetrics]]:
        """
        Generate email with streaming and metrics.
        
        Args:
            context: Email context
            
        Yields:
            Tuples of (text_chunk, current_metrics)
        """
        start_time = time.time()
        ttft = None
        chunks_received = 0
        tokens_generated = 0
        
        try:
            async for chunk in self.generator.generate_email_stream(context):
                # Record TTFT on first chunk
                if ttft is None:
                    ttft = time.time() - start_time
                    logger.info(f"TTFT: {ttft:.3f}s")
                
                chunks_received += 1
                tokens_generated += len(chunk.split())
                
                # Calculate current metrics
                current_time = time.time() - start_time
                metrics = StreamMetrics(
                    ttft=ttft,
                    total_time=current_time,
                    tokens_generated=tokens_generated,
                    chunks_received=chunks_received
                )
                
                yield chunk, metrics
            
            # Final metrics
            total_time = time.time() - start_time
            final_metrics = StreamMetrics(
                ttft=ttft or 0.0,
                total_time=total_time,
                tokens_generated=tokens_generated,
                chunks_received=chunks_received
            )
            
            logger.info(
                f"Streaming complete: {total_time:.2f}s, "
                f"{tokens_generated} tokens, {chunks_received} chunks"
            )
            
        except Exception as e:
            logger.error(f"Streaming failed: {str(e)}")
            raise


# Global streaming generator instance
streaming_generator = StreamingEmailGenerator()

# Made with Bob
