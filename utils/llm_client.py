"""Claude API client with retry logic."""

import os
import time
from typing import Optional, Dict, Any
from anthropic import Anthropic, APIError, RateLimitError
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


class ClaudeClient:
    """Wrapper for Claude API with retry and error handling."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4",
        max_tokens: int = 4096,
        temperature: float = 0.0
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        
        self.client = Anthropic(api_key=self.api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 3,
        retry_delay: int = 2
    ) -> str:
        """Generate response from Claude with retry logic.
        
        Args:
            system_prompt: System instructions
            user_prompt: User message
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries (seconds)
            
        Returns:
            Generated text response
            
        Raises:
            APIError: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"Calling Claude API (attempt {attempt + 1}/{max_retries})")
                
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ]
                )
                
                response_text = message.content[0].text
                logger.info(f"API call successful. Response length: {len(response_text)} chars")
                
                return response_text
                
            except RateLimitError as e:
                logger.warning(f"Rate limit hit: {e}. Retrying in {retry_delay}s...")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise
                    
            except APIError as e:
                logger.error(f"API error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise
                    
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise
                
        raise APIError("Max retries exceeded")
