"""Insight Agent - Generates testable hypotheses."""

from typing import Dict, Any
from agents.base_agent import BaseAgent
from prompts.insight_prompts import INSIGHT_AGENT_SYSTEM_PROMPT, format_insight_agent_prompt
from utils.validators import InsightAgentOutput, Hypothesis, DataSummary
from pydantic import ValidationError


class InsightAgent(BaseAgent):
    """Agent that generates hypotheses about performance."""
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_name="InsightAgent",
            system_prompt=INSIGHT_AGENT_SYSTEM_PROMPT,
            **kwargs
        )
    
    def execute(
        self,
        query: str,
        data_summary: DataSummary,
        focus_dimension: str = "all dimensions"
    ) -> InsightAgentOutput:
        """Generate hypotheses to explain performance patterns.
        
        Args:
            query: User's question
            data_summary: Summary from DataAgent
            focus_dimension: Specific dimension to focus on
            
        Returns:
            InsightAgentOutput with hypotheses
        """
        self._log_event("hypothesis_generation_start", {"query": query})
        
        # Format prompt
        user_prompt = format_insight_agent_prompt(
            query=query,
            data_summary=data_summary.model_dump(),
            focus_dimension=focus_dimension
        )
        
        # Call LLM
        response = self._call_llm(user_prompt)
        
        # Parse response
        output_dict = self._parse_json_response(response)
        
        # Validate structure
        self._validate_output(output_dict, ["hypotheses_generated", "reasoning"])
        
        # Convert to Pydantic models
        try:
            hypotheses = [
                Hypothesis(**hyp) for hyp in output_dict["hypotheses_generated"]
            ]
            
            insight_output = InsightAgentOutput(
                hypotheses_generated=hypotheses,
                data_summary_used=data_summary,
                reasoning=output_dict["reasoning"],
                confidence_in_hypotheses=output_dict.get("confidence_in_hypotheses", 0.7)
            )
            
            self._log_event("hypothesis_generation_success", {
                "num_hypotheses": len(hypotheses),
                "avg_confidence": sum(
                    1.0 if h.confidence == "high" else 0.5 if h.confidence == "medium" else 0.2
                    for h in hypotheses
                ) / len(hypotheses)
            })
            
            return insight_output
            
        except ValidationError as e:
            self._log_event("validation_error", {"error": str(e)}, status="error")
            raise ValueError(f"Hypothesis validation failed: {e}")
