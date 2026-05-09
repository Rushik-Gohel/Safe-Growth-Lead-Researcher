"""Security guardrails for prompt injection detection and input validation."""

import re
import logging
from typing import Optional, List, Tuple
from dataclasses import dataclass

from ..core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of input validation."""
    
    is_safe: bool
    reason: Optional[str] = None
    threat_level: str = "none"  # none, low, medium, high
    detected_patterns: List[str] = None
    
    def __post_init__(self):
        if self.detected_patterns is None:
            self.detected_patterns = []


class SecurityGuardrails:
    """
    Security layer for detecting prompt injection and malicious inputs.
    Uses regex patterns and heuristics to identify threats.
    """
    
    # Prompt injection patterns
    INJECTION_PATTERNS = [
        # Direct instruction overrides
        (r"ignore\s+(all\s+)?(previous|above|prior)\s+instructions?", "instruction_override"),
        (r"disregard\s+(all\s+)?(previous|above|prior)\s+instructions?", "instruction_override"),
        (r"forget\s+(all\s+)?(previous|above|prior)\s+instructions?", "instruction_override"),
        
        # System prompt manipulation
        (r"you\s+are\s+now", "role_manipulation"),
        (r"act\s+as\s+(a\s+)?(?!lead|researcher)", "role_manipulation"),
        (r"pretend\s+to\s+be", "role_manipulation"),
        (r"simulate\s+being", "role_manipulation"),
        
        # Jailbreak attempts
        (r"DAN\s+mode", "jailbreak"),
        (r"developer\s+mode", "jailbreak"),
        (r"evil\s+mode", "jailbreak"),
        (r"unrestricted\s+mode", "jailbreak"),
        
        # System access attempts
        (r"system\s+prompt", "system_access"),
        (r"show\s+me\s+your\s+(instructions|prompt|rules)", "system_access"),
        (r"what\s+are\s+your\s+(instructions|rules)", "system_access"),
        
        # Code injection
        (r"<script[^>]*>", "code_injection"),
        (r"javascript:", "code_injection"),
        (r"eval\s*\(", "code_injection"),
        (r"exec\s*\(", "code_injection"),
        
        # SQL injection patterns
        (r";\s*drop\s+table", "sql_injection"),
        (r"union\s+select", "sql_injection"),
        (r"--\s*$", "sql_injection"),
        
        # Excessive special characters (potential obfuscation)
        (r"[^\w\s]{10,}", "obfuscation"),
        
        # Repeated instructions
        (r"(repeat|say|write|output)\s+.{0,20}\1", "repetition_attack"),
    ]
    
    # Suspicious keywords
    SUSPICIOUS_KEYWORDS = [
        "bypass", "override", "jailbreak", "exploit", "hack",
        "vulnerability", "backdoor", "malicious", "inject"
    ]
    
    def __init__(self, max_input_length: Optional[int] = None):
        """
        Initialize security guardrails.
        
        Args:
            max_input_length: Maximum allowed input length
        """
        self.max_input_length = max_input_length or settings.max_input_length
        self.enabled = settings.enable_guardrails
        
        # Compile regex patterns for performance
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), name)
            for pattern, name in self.INJECTION_PATTERNS
        ]
        
        logger.info(
            f"SecurityGuardrails initialized: enabled={self.enabled}, "
            f"max_length={self.max_input_length}"
        )
    
    def validate_input(self, user_input: str) -> ValidationResult:
        """
        Validate user input for security threats.
        
        Args:
            user_input: User-provided input string
            
        Returns:
            ValidationResult with safety status and details
        """
        if not self.enabled:
            return ValidationResult(is_safe=True)
        
        # Check input length
        if len(user_input) > self.max_input_length:
            return ValidationResult(
                is_safe=False,
                reason=f"Input exceeds maximum length of {self.max_input_length} characters",
                threat_level="low"
            )
        
        # Check for empty input
        if not user_input.strip():
            return ValidationResult(
                is_safe=False,
                reason="Empty input provided",
                threat_level="low"
            )
        
        detected_patterns = []
        threat_level = "none"
        
        # Check against injection patterns
        for pattern, pattern_name in self.compiled_patterns:
            if pattern.search(user_input):
                detected_patterns.append(pattern_name)
                logger.warning(f"Detected pattern: {pattern_name} in input")
        
        # Check for suspicious keywords
        lower_input = user_input.lower()
        suspicious_found = [
            keyword for keyword in self.SUSPICIOUS_KEYWORDS
            if keyword in lower_input
        ]
        
        if suspicious_found:
            detected_patterns.extend([f"keyword:{kw}" for kw in suspicious_found])
        
        # Determine threat level
        if detected_patterns:
            if any(p in ["instruction_override", "jailbreak", "code_injection"] 
                   for p in detected_patterns):
                threat_level = "high"
            elif any(p in ["role_manipulation", "system_access"] 
                     for p in detected_patterns):
                threat_level = "medium"
            else:
                threat_level = "low"
        
        # Build result
        if detected_patterns:
            return ValidationResult(
                is_safe=False,
                reason=f"Potential security threat detected: {', '.join(set(detected_patterns))}",
                threat_level=threat_level,
                detected_patterns=detected_patterns
            )
        
        return ValidationResult(is_safe=True)
    
    def sanitize_input(self, user_input: str) -> str:
        """
        Sanitize user input by removing potentially harmful content.
        
        Args:
            user_input: Raw user input
            
        Returns:
            Sanitized input string
        """
        # Remove HTML tags
        sanitized = re.sub(r'<[^>]+>', '', user_input)
        
        # Remove script tags and content
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # Trim to max length
        if len(sanitized) > self.max_input_length:
            sanitized = sanitized[:self.max_input_length]
        
        return sanitized.strip()
    
    def get_security_response(self, validation_result: ValidationResult) -> str:
        """
        Generate appropriate security response message.
        
        Args:
            validation_result: Result from validation
            
        Returns:
            User-friendly security message
        """
        if validation_result.threat_level == "high":
            return (
                "⚠️ Security Alert: Your input contains patterns that may be attempting "
                "to manipulate the system. Please provide a legitimate LinkedIn URL or "
                "company name for research."
            )
        elif validation_result.threat_level == "medium":
            return (
                "⚠️ Warning: Your input contains suspicious patterns. Please ensure you're "
                "providing a valid LinkedIn URL or company name."
            )
        else:
            return (
                "❌ Invalid input. Please provide a LinkedIn URL or company name."
            )
    
    def validate_and_sanitize(self, user_input: str) -> Tuple[bool, str, Optional[str]]:
        """
        Validate and sanitize input in one call.
        
        Args:
            user_input: Raw user input
            
        Returns:
            Tuple of (is_safe, sanitized_input, error_message)
        """
        # First validate
        validation_result = self.validate_input(user_input)
        
        if not validation_result.is_safe:
            error_message = self.get_security_response(validation_result)
            return False, "", error_message
        
        # Then sanitize
        sanitized = self.sanitize_input(user_input)
        
        return True, sanitized, None


# Global guardrails instance
guardrails = SecurityGuardrails()

# Made with Bob
