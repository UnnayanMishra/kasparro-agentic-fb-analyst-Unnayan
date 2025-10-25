"""Main orchestrator that manages agent execution flow."""

from typing import Dict, Any, Optional
import logging

from agents.planner_agent import PlannerAgent
from agents.data_agent import DataAgent
from agents.insight_agent import InsightAgent
from agents.evaluator_agent import EvaluatorAgent
from agents.creative_generator import CreativeGeneratorAgent
from utils.validators import TaskPlan, DataSummary, FinalReport
from utils.llm_client import ClaudeClient
from utils.logger import StructuredLogger
from datetime import datetime

logger = logging.getLogger(__name__)


class AgenticOrchestrator:
    """Orchestrator that manages the multi-agent workflow."""
    
    def __init__(
        self,
        llm_client: Optional[ClaudeClient] = None,
        structured_logger: Optional[StructuredLogger] = None,
        max_replans: int = 2
    ):
        """Initialize orchestrator.
        
        Args:
            llm_client: Shared Claude client
            structured_logger: Shared logger
            max_replans: Maximum replanning iterations
        """
        self.llm_client = llm_client or ClaudeClient()
        self.structured_logger = structured_logger or StructuredLogger()
        self.max_replans = max_replans
        
        # Initialize all agents
        self.planner = PlannerAgent(
            llm_client=self.llm_client,
            structured_logger=self.structured_logger
        )
        self.data_agent = DataAgent(
            llm_client=self.llm_client,
            structured_logger=self.structured_logger
        )
        self.insight_agent = InsightAgent(
            llm_client=self.llm_client,
            structured_logger=self.structured_logger
        )
        self.evaluator = EvaluatorAgent(
            llm_client=self.llm_client,
            structured_logger=self.structured_logger
        )
        self.creative_generator = CreativeGeneratorAgent(
            llm_client=self.llm_client,
            structured_logger=self.structured_logger
        )
        
        logger.info("Orchestrator initialized with all agents")
    
    def execute(
        self,
        query: str,
        data_file_path: str = "data/raw/fb_ads_data.csv"
    ) -> FinalReport:
        """Execute the full agentic workflow.
        
        Args:
            query: User's analytical question
            data_file_path: Path to data file
            
        Returns:
            FinalReport with all insights and recommendations
        """
        logger.info(f"Starting workflow for query: {query}")
        
        iteration = 0
        
        while iteration <= self.max_replans:
            iteration += 1
            logger.info(f"=== Iteration {iteration} ===")
            
            # Step 1: Data Agent - Always load data first
            logger.info("Step 1: Loading and summarizing data...")
            data_summary = self.data_agent.execute(data_file_path=data_file_path)
            
            # Step 2: Planner - Create task plan
            logger.info("Step 2: Creating task plan...")
            data_context = {
                'start_date': data_summary.date_range['start'],
                'end_date': data_summary.date_range['end'],
                'total_spend': data_summary.total_spend,
                'overall_roas': data_summary.overall_roas
            }
            
            task_plan = self.planner.execute(
                query=query,
                data_context=data_context
            )
            
            logger.info(f"Plan created with {len(task_plan.tasks)} tasks")
            
            # Step 3: Insight Agent - Generate hypotheses
            logger.info("Step 3: Generating hypotheses...")
            insight_output = self.insight_agent.execute(
                query=query,
                data_summary=data_summary
            )
            
            logger.info(f"Generated {len(insight_output.hypotheses_generated)} hypotheses")
            
            # Step 4: Evaluator - Validate hypotheses
            logger.info("Step 4: Validating hypotheses...")
            evaluator_output = self.evaluator.execute(
                hypotheses=insight_output.hypotheses_generated,
                data_file_path=data_file_path
            )
            
            logger.info(f"Validated {len(evaluator_output.validated_insights)} insights")
            
            # Check if replanning needed
            if evaluator_output.needs_replan and iteration < self.max_replans:
                logger.warning(f"Replanning needed: {evaluator_output.replan_reason}")
                continue
            
            # Step 5: Creative Generator - Generate recommendations
            logger.info("Step 5: Generating creative recommendations...")
            creative_analysis = self.creative_generator.execute(
                validated_insights=evaluator_output.validated_insights,
                data_file_path=data_file_path
            )
            
            logger.info(f"Generated {len(creative_analysis.recommendations)} recommendations")
            
            # Create final report
            report = self._create_final_report(
                query=query,
                data_summary=data_summary,
                validated_insights=evaluator_output.validated_insights,
                creative_analysis=creative_analysis,
                total_iterations=iteration,
                validation_results=evaluator_output.validation_results
            )
            
            logger.info("Workflow completed successfully")
            return report
        
        # If we exhausted all replans
        logger.error("Max replanning iterations reached")
        raise RuntimeError("Failed to generate satisfactory insights after max replans")
    
    def _create_final_report(
        self,
        query: str,
        data_summary: DataSummary,
        validated_insights: list,
        creative_analysis,
        total_iterations: int,
        validation_results: list
    ) -> FinalReport:
        """Create final report combining all outputs.
        
        Args:
            query: Original query
            data_summary: Data summary
            validated_insights: Validated insights
            creative_analysis: Creative recommendations
            total_iterations: Number of iterations
            validation_results: All validation results
            
        Returns:
            FinalReport object
        """
        # Generate executive summary
        exec_summary = self._generate_executive_summary(
            validated_insights,
            creative_analysis
        )
        
        # Calculate validation success rate
        total_hypotheses = len(validation_results)
        validated_count = sum(1 for r in validation_results if r.status == "validated")
        success_rate = validated_count / total_hypotheses if total_hypotheses > 0 else 0
        
        return FinalReport(
            report_id=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            generated_at=datetime.now(),
            original_query=query,
            analysis_period=data_summary.date_range,
            executive_summary=exec_summary,
            key_insights=validated_insights,
            creative_recommendations=creative_analysis.recommendations,
            data_summary=data_summary,
            total_hypotheses_tested=total_hypotheses,
            validation_success_rate=round(success_rate, 2),
            total_iterations=total_iterations
        )
    
    def _generate_executive_summary(
        self,
        insights: list,
        creative_analysis
    ) -> str:
        """Generate executive summary.
        
        Args:
            insights: Validated insights
            creative_analysis: Creative analysis
            
        Returns:
            Executive summary text
        """
        if not insights:
            return "No significant insights found in the analysis."
        
        top_insight = max(insights, key=lambda x: x.impact_score)
        top_rec = max(
            creative_analysis.recommendations,
            key=lambda x: x.priority_score
        ) if creative_analysis.recommendations else None
        
        summary = f"Analysis identified {len(insights)} key insights. "
        summary += f"Top finding: {top_insight.title}. "
        
        if top_rec:
            summary += f"Primary recommendation: {top_rec.action}."
        
        return summary
