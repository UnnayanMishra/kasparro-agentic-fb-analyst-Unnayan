"""Evaluator Agent - Validates hypotheses with statistical tests."""

from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from prompts.evaluator_prompts import EVALUATOR_AGENT_SYSTEM_PROMPT, format_evaluator_prompt
from utils.validators import (
    EvaluatorOutput, ValidationResult, Hypothesis, Insight,
    HypothesisStatus
)
from utils.data_processors import load_fb_ads_data
from pydantic import ValidationError
import pandas as pd
from scipy import stats
import numpy as np


class EvaluatorAgent(BaseAgent):
    """Agent that validates hypotheses with statistical rigor."""
    
    def __init__(self, confidence_threshold: float = 0.7, **kwargs):
        super().__init__(
            agent_name="EvaluatorAgent",
            system_prompt=EVALUATOR_AGENT_SYSTEM_PROMPT,
            **kwargs
        )
        self.confidence_threshold = confidence_threshold
    
    def execute(
        self,
        hypotheses: List[Hypothesis],
        data_file_path: str = "data/raw/fb_ads_data.csv"
    ) -> EvaluatorOutput:
        """Validate hypotheses with statistical tests.
        
        Args:
            hypotheses: List of hypotheses to validate
            data_file_path: Path to data file
            
        Returns:
            EvaluatorOutput with validation results
        """
        self._log_event("validation_start", {"num_hypotheses": len(hypotheses)})
        
        # Load data for validation
        df = load_fb_ads_data(data_file_path)
        
        validation_results = []
        validated_insights = []
        rejected_hypotheses = []
        
        for hypothesis in hypotheses:
            result = self._validate_hypothesis(hypothesis, df)
            validation_results.append(result)
            
            if result.status == HypothesisStatus.VALIDATED:
                # Create Insight from validated hypothesis
                insight = self._create_insight(hypothesis, result, df)
                validated_insights.append(insight)
            else:
                rejected_hypotheses.append(hypothesis.hypothesis_id)
        
        # Determine if replanning needed
        num_validated = len(validated_insights)
        needs_replan = num_validated < 2
        replan_reason = None
        
        if needs_replan:
            replan_reason = f"Only {num_validated} hypothesis validated. Need different analytical approach."
        
        evaluator_output = EvaluatorOutput(
            validation_results=validation_results,
            validated_insights=validated_insights,
            rejected_hypotheses=rejected_hypotheses,
            needs_replan=needs_replan,
            replan_reason=replan_reason,
            suggested_focus_areas=self._suggest_focus_areas(validation_results)
        )
        
        self._log_event("validation_complete", {
            "validated": num_validated,
            "rejected": len(rejected_hypotheses),
            "needs_replan": needs_replan
        })
        
        return evaluator_output
    
    def _validate_hypothesis(
        self,
        hypothesis: Hypothesis,
        df: pd.DataFrame
    ) -> ValidationResult:
        """Validate a single hypothesis with statistical test.
        
        Args:
            hypothesis: Hypothesis to validate
            df: Full dataset
            
        Returns:
            ValidationResult
        """
        try:
            metric = hypothesis.metric_to_test
            
            # Segment data if specified
            if hypothesis.segment_dimension and hypothesis.segment_value:
                group_a = df[df[hypothesis.segment_dimension] == hypothesis.segment_value]
                group_b = df[df[hypothesis.segment_dimension] != hypothesis.segment_value]
            else:
                # Time-based comparison if no segment specified
                mid_point = len(df) // 2
                group_a = df.iloc[:mid_point]
                group_b = df.iloc[mid_point:]
            
            # Check sample sizes
            if len(group_a) < 30 or len(group_b) < 30:
                return ValidationResult(
                    hypothesis_id=hypothesis.hypothesis_id,
                    status=HypothesisStatus.NEEDS_MORE_DATA,
                    confidence_score=0.3,
                    verdict=f"Insufficient sample size (n_a={len(group_a)}, n_b={len(group_b)})",
                    actionability="Collect more data before drawing conclusions"
                )
            
            # Perform t-test
            stat, p_value = stats.ttest_ind(group_a[metric], group_b[metric])
            
            # Calculate effect size (Cohen's d)
            mean_a = group_a[metric].mean()
            mean_b = group_b[metric].mean()
            pooled_std = np.sqrt((group_a[metric].std()**2 + group_b[metric].std()**2) / 2)
            effect_size = abs(mean_a - mean_b) / pooled_std if pooled_std > 0 else 0
            
            # Calculate confidence score
            sig_score = 1.0 if p_value < 0.05 else 0.5 if p_value < 0.10 else 0.0
            effect_score = 1.0 if effect_size > 0.5 else 0.6 if effect_size > 0.3 else 0.3
            sample_score = 1.0 if min(len(group_a), len(group_b)) > 100 else 0.7
            
            confidence_score = (0.4 * sig_score + 0.4 * effect_score + 0.2 * sample_score)
            
            # Determine status
            if p_value < 0.05 and effect_size > 0.3:
                status = HypothesisStatus.VALIDATED
                verdict = f"Hypothesis validated: {hypothesis.segment_value if hypothesis.segment_value else 'Group A'} shows {abs(mean_a - mean_b):.2f} {metric} difference (p={p_value:.3f}, d={effect_size:.2f})"
                actionability = f"Statistically significant result. {'Scale' if mean_a > mean_b else 'Optimize'} {hypothesis.segment_value if hypothesis.segment_value else 'this segment'}"
            else:
                status = HypothesisStatus.REJECTED
                verdict = f"Hypothesis rejected: No significant difference found (p={p_value:.3f}, effect_size={effect_size:.2f})"
                actionability = "Focus on other hypotheses with stronger evidence"
            
            return ValidationResult(
                hypothesis_id=hypothesis.hypothesis_id,
                status=status,
                confidence_score=round(confidence_score, 3),
                statistical_test="independent t-test",
                p_value=round(p_value, 4),
                effect_size=round(effect_size, 3),
                supporting_metrics={
                    "group_a_mean": round(mean_a, 3),
                    "group_b_mean": round(mean_b, 3),
                    "difference": round(abs(mean_a - mean_b), 3),
                    "sample_size_a": len(group_a),
                    "sample_size_b": len(group_b)
                },
                verdict=verdict,
                actionability=actionability
            )
            
        except Exception as e:
            self._log_event("validation_error", {
                "hypothesis_id": hypothesis.hypothesis_id,
                "error": str(e)
            }, status="error")
            
            return ValidationResult(
                hypothesis_id=hypothesis.hypothesis_id,
                status=HypothesisStatus.NEEDS_MORE_DATA,
                confidence_score=0.0,
                verdict=f"Validation failed: {str(e)}",
                actionability="Unable to validate with current data"
            )
    
    def _create_insight(
        self,
        hypothesis: Hypothesis,
        validation: ValidationResult,
        df: pd.DataFrame
    ) -> Insight:
        """Create an Insight from validated hypothesis.
        
        Args:
            hypothesis: Original hypothesis
            validation: Validation result
            df: Dataset
            
        Returns:
            Insight object
        """
        # Estimate revenue impact
        avg_daily_revenue = df['revenue'].sum() / len(df['date'].unique())
        estimated_impact = avg_daily_revenue * 0.1 * validation.confidence_score  # 10% base impact
        
        return Insight(
            insight_id=f"insight_{hypothesis.hypothesis_id}",
            title=hypothesis.statement[:80],
            description=hypothesis.rationale,
            hypothesis=hypothesis,
            validation=validation,
            impact_score=round(validation.confidence_score * 10, 1),
            estimated_revenue_impact=round(estimated_impact, 2),
            category="performance",
            urgency="high" if validation.confidence_score > 0.8 else "medium",
            time_period_analyzed={
                "start": df['date'].min().strftime('%Y-%m-%d'),
                "end": df['date'].max().strftime('%Y-%m-%d')
            },
            affected_campaigns=df['campaign_name'].unique().tolist()[:3]
        )
    
    def _suggest_focus_areas(self, validation_results: List[ValidationResult]) -> List[str]:
        """Suggest areas to focus on based on validation results.
        
        Args:
            validation_results: List of validation results
            
        Returns:
            List of focus area suggestions
        """
        suggestions = []
        
        rejected_count = sum(1 for r in validation_results if r.status == HypothesisStatus.REJECTED)
        
        if rejected_count > len(validation_results) / 2:
            suggestions.append("Consider different analytical dimensions (e.g., time-based, audience-based)")
            suggestions.append("Look for interaction effects between variables")
        
        return suggestions
