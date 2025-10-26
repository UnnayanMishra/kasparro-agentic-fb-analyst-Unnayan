"""OpenAI API client with retry logic."""

import os
import time
from typing import Optional
from openai import OpenAI, APIError, RateLimitError, APIConnectionError
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper for OpenAI API with retry and error handling."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",  # Using gpt-4o-mini for cost efficiency
        max_tokens: int = 4096,
        temperature: float = 0.0
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        logger.info(f"Initialized OpenAI client with model: {model}")
        
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 3,
        retry_delay: int = 2
    ) -> str:
        """Generate response from OpenAI with retry logic.
        
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
                logger.info(f"Calling OpenAI API (attempt {attempt + 1}/{max_retries})")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                
                response_text = response.choices[0].message.content
                logger.info(f"API call successful. Response length: {len(response_text)} chars")
                
                return response_text
                
            except RateLimitError as e:
                logger.warning(f"Rate limit hit: {e}. Retrying in {retry_delay}s...")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise
                    
            except APIConnectionError as e:
                logger.error(f"Connection error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
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
                
        raise Exception("Max retries exceeded")


# Alias for backward compatibility
ClaudeClient = LLMClient
