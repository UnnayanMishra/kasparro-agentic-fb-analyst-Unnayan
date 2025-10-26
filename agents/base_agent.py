"""Base Agent class with common functionality."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import json
from pathlib import Path
import logging

from utils.llm_client import LLMClient
from utils.logger import StructuredLogger

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    def __init__(
        self,
        agent_name: str,
        system_prompt: str,
        llm_client: Optional[LLMClient] = None,
        structured_logger: Optional[StructuredLogger] = None
    ):
        """Initialize base agent.
        
        Args:
            agent_name: Name of the agent
            system_prompt: System prompt defining agent behavior
            llm_client: LLM API client (creates new if None)
            structured_logger: Logger instance
        """
        self.agent_name = agent_name
        self.system_prompt = system_prompt
        self.llm_client = llm_client or LLMClient()
        self.structured_logger = structured_logger
        
        logger.info(f"Initialized {self.agent_name}")
        
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the agent's task.
        
        Must be implemented by subclasses.
        
        Returns:
            Dictionary with execution results
        """
        pass
    
    def _call_llm(self, user_prompt: str) -> str:
        """Call LLM API with error handling.
        
        Args:
            user_prompt: User message
            
        Returns:
            LLM response text
        """
        try:
            self._log_event("llm_call_start", {"prompt_length": len(user_prompt)})
            
            response = self.llm_client.generate(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt
            )
            
            self._log_event("llm_call_success", {
                "response_length": len(response)
            })
            
            return response
            
        except Exception as e:
            self._log_event("llm_call_error", {"error": str(e)}, status="error")
            raise
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Extract and parse JSON from LLM response.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Parsed JSON as dictionary
        """
        try:
            # Try to find JSON in markdown code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            
            parsed = json.loads(json_str)
            self._log_event("json_parse_success", {"keys": list(parsed.keys())})
            
            return parsed
            
        except json.JSONDecodeError as e:
            self._log_event("json_parse_error", {
                "error": str(e),
                "response_preview": response[:200]
            }, status="error")
            
            # Try to extract JSON more aggressively
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            
            raise ValueError(f"Could not parse JSON from response: {response[:200]}...")
    
    def _validate_output(self, output: Dict[str, Any], required_keys: list) -> bool:
        """Validate that output contains required keys.
        
        Args:
            output: Output dictionary to validate
            required_keys: List of required key names
            
        Returns:
            True if valid, raises ValueError if not
        """
        missing_keys = [key for key in required_keys if key not in output]
        
        if missing_keys:
            self._log_event("validation_error", {
                "missing_keys": missing_keys
            }, status="error")
            raise ValueError(f"Missing required keys: {missing_keys}")
        
        self._log_event("validation_success", {"validated_keys": required_keys})
        return True
    
    def _log_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        status: str = "success"
    ):
        """Log an event if logger is available.
        
        Args:
            event_type: Type of event
            data: Event data
            status: Event status
        """
        if self.structured_logger:
            self.structured_logger.log_agent_execution(
                agent_name=self.agent_name,
                event_type=event_type,
                data=data,
                status=status
            )
        
        # Also log to standard logger
        logger.info(f"[{self.agent_name}] {event_type}: {status}")
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.agent_name})"
