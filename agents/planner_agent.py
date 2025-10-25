"""Planner Agent - Decomposes queries into task plans."""

from typing import Dict, Any
from agents.base_agent import BaseAgent
from prompts.planner_prompts import PLANNER_SYSTEM_PROMPT, format_planner_prompt
from utils.validators import TaskPlan, Task
from pydantic import ValidationError


class PlannerAgent(BaseAgent):
    """Agent that creates strategic task plans."""
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_name="PlannerAgent",
            system_prompt=PLANNER_SYSTEM_PROMPT,
            **kwargs
        )
    
    def execute(
        self,
        query: str,
        data_context: Dict[str, Any]
    ) -> TaskPlan:
        """Create a task plan for the given query.
        
        Args:
            query: User's analytical question
            data_context: Context about the dataset
            
        Returns:
            TaskPlan object with structured tasks
        """
        self._log_event("plan_creation_start", {"query": query})
        
        # Format the prompt
        user_prompt = format_planner_prompt(query, data_context)
        
        # Call LLM
        response = self._call_llm(user_prompt)
        
        # Parse response
        plan_dict = self._parse_json_response(response)
        
        # Validate required keys
        self._validate_output(plan_dict, ["query", "tasks", "reasoning"])
        
        # Convert to Pydantic model
        try:
            # Convert task dicts to Task objects
            tasks = [Task(**task) for task in plan_dict["tasks"]]
            
            task_plan = TaskPlan(
                query=plan_dict["query"],
                tasks=tasks,
                reasoning=plan_dict["reasoning"],
                expected_insights=plan_dict.get("expected_insights", [])
            )
            
            self._log_event("plan_creation_success", {
                "num_tasks": len(tasks),
                "agents_involved": list(set(t.assigned_agent for t in tasks))
            })
            
            return task_plan
            
        except ValidationError as e:
            self._log_event("validation_error", {"error": str(e)}, status="error")
            raise ValueError(f"Plan validation failed: {e}")
