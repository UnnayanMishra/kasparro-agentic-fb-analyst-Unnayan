"""Pydantic schemas for agent communication and data validation."""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


# ============================================================
# ENUMS FOR VALIDATION
# ============================================================

class ConfidenceLevel(str, Enum):
    """Confidence levels for hypotheses and insights."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class HypothesisStatus(str, Enum):
    """Status of hypothesis validation."""
    VALIDATED = "validated"
    REJECTED = "rejected"
    NEEDS_MORE_DATA = "needs_more_data"


class CreativeType(str, Enum):
    """Types of creative formats."""
    IMAGE = "Image"
    VIDEO = "Video"
    UGC = "UGC"
    CAROUSEL = "Carousel"


class Platform(str, Enum):
    """Ad platforms."""
    FACEBOOK = "Facebook"
    INSTAGRAM = "Instagram"


# ============================================================
# CORE DATA MODELS
# ============================================================

class Task(BaseModel):
    """Individual task in the agent workflow."""
    task_id: str = Field(..., description="Unique task identifier")
    description: str = Field(..., description="What the task should accomplish")
    assigned_agent: str = Field(..., description="Agent responsible for this task")
    dependencies: List[str] = Field(default_factory=list, description="Task IDs that must complete first")
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
    output: Optional[Any] = None


class TaskPlan(BaseModel):
    """Complete task plan from Planner Agent."""
    query: str = Field(..., description="Original user query")
    tasks: List[Task] = Field(..., description="Ordered list of tasks")
    reasoning: str = Field(..., description="Why this plan was chosen")
    expected_insights: List[str] = Field(..., description="Expected types of insights")


# ============================================================
# HYPOTHESIS & INSIGHT MODELS
# ============================================================

class Hypothesis(BaseModel):
    """A testable hypothesis about ad performance."""
    hypothesis_id: str = Field(..., description="Unique identifier")
    statement: str = Field(..., description="Clear, testable statement")
    rationale: str = Field(..., description="Why this hypothesis matters")
    
    # Metrics to validate
    metric_to_test: str = Field(..., description="Primary metric (e.g., 'roas', 'ctr')")
    expected_direction: Literal["increase", "decrease", "change"] = Field(
        ..., description="Expected change direction"
    )
    
    # Segmentation
    segment_dimension: Optional[str] = Field(None, description="Dimension to segment by")
    segment_value: Optional[str] = Field(None, description="Specific segment value")
    
    # Confidence & validation
    confidence: ConfidenceLevel = Field(..., description="Initial confidence level")
    supporting_evidence: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class ValidationResult(BaseModel):
    """Result of hypothesis validation."""
    hypothesis_id: str
    status: HypothesisStatus
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="0-1 confidence")
    
    # Statistical evidence
    statistical_test: Optional[str] = Field(None, description="Test used (e.g., t-test)")
    p_value: Optional[float] = Field(None, ge=0.0, le=1.0)
    effect_size: Optional[float] = Field(None, description="Magnitude of effect")
    
    # Quantitative support
    supporting_metrics: Dict[str, float] = Field(default_factory=dict)
    counterevidence: List[str] = Field(default_factory=list)
    
    # Final verdict
    verdict: str = Field(..., description="Clear explanation of validation result")
    actionability: str = Field(..., description="What action to take based on this")
    
    class Config:
        use_enum_values = True
    
    @field_validator('confidence_score')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Confidence score must be between 0 and 1")
        return round(v, 3)


class Insight(BaseModel):
    """Validated insight with actionable recommendations."""
    insight_id: str
    title: str = Field(..., description="Short, compelling title")
    description: str = Field(..., description="Full explanation of the insight")
    
    # Associated hypothesis
    hypothesis: Hypothesis
    validation: ValidationResult
    
    # Impact assessment
    impact_score: float = Field(..., ge=0.0, le=10.0, description="0-10 business impact")
    estimated_revenue_impact: Optional[float] = Field(None, description="Expected $ impact")
    
    # Categorization
    category: Literal["performance", "creative", "audience", "platform", "geographic"] = Field(
        ..., description="Type of insight"
    )
    urgency: Literal["critical", "high", "medium", "low"] = "medium"
    
    # Context
    time_period_analyzed: Dict[str, str] = Field(
        ..., description="Date range analyzed"
    )
    affected_campaigns: List[str] = Field(default_factory=list)


# ============================================================
# CREATIVE RECOMMENDATION MODELS
# ============================================================

class CreativeRecommendation(BaseModel):
    """Specific creative recommendation based on data."""
    recommendation_id: str
    recommendation_type: Literal["new_creative", "optimize_existing", "pause_creative", "scale_creative"]
    
    # What to do
    action: str = Field(..., description="Specific action to take")
    creative_type: CreativeType
    target_platform: Platform
    
    # Why
    data_driven_rationale: str = Field(..., description="Data evidence supporting this")
    expected_improvement: Dict[str, float] = Field(
        ..., description="Expected metric improvements (e.g., {'roas': 1.2, 'ctr': 0.05})"
    )
    
    # How
    implementation_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Specific details like copy angles, visual elements, etc."
    )
    
    # Priority
    priority_score: float = Field(..., ge=0.0, le=10.0)
    estimated_budget_allocation: Optional[float] = None
    
    # Supporting data
    reference_examples: List[str] = Field(
        default_factory=list,
        description="Ad IDs or creative examples that performed well"
    )
    
    class Config:
        use_enum_values = True


class CreativeAnalysis(BaseModel):
    """Complete creative performance analysis."""
    analysis_date: datetime = Field(default_factory=datetime.now)
    
    # Top performers
    top_performing_creatives: List[Dict[str, Any]] = Field(default_factory=list)
    underperforming_creatives: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Patterns identified
    winning_patterns: List[str] = Field(default_factory=list)
    losing_patterns: List[str] = Field(default_factory=list)
    
    # Recommendations
    recommendations: List[CreativeRecommendation]
    
    # Summary metrics
    overall_creative_performance: Dict[str, float] = Field(default_factory=dict)


# ============================================================
# AGENT INPUT/OUTPUT MODELS
# ============================================================

class DataSummary(BaseModel):
    """Summary of dataset from Data Agent."""
    total_rows: int
    date_range: Dict[str, str]
    campaigns: List[str]
    
    # Aggregate metrics
    total_spend: float
    total_revenue: float
    overall_roas: float
    
    # Breakdowns
    performance_by_creative_type: Dict[str, Dict[str, float]]
    performance_by_platform: Dict[str, Dict[str, float]]
    performance_by_country: Dict[str, Dict[str, float]]
    
    # Time series
    daily_metrics: Optional[List[Dict[str, Any]]] = None
    
    # Anomalies detected
    anomalies: List[str] = Field(default_factory=list)


class InsightAgentOutput(BaseModel):
    """Output from Insight Agent."""
    hypotheses_generated: List[Hypothesis]
    data_summary_used: DataSummary
    reasoning: str = Field(..., description="Overall reasoning process")
    confidence_in_hypotheses: float = Field(..., ge=0.0, le=1.0)


class EvaluatorOutput(BaseModel):
    """Output from Evaluator Agent."""
    validation_results: List[ValidationResult]
    validated_insights: List[Insight]
    rejected_hypotheses: List[str] = Field(default_factory=list)
    
    # Feedback for replanning
    needs_replan: bool = False
    replan_reason: Optional[str] = None
    suggested_focus_areas: List[str] = Field(default_factory=list)


class FinalReport(BaseModel):
    """Final report combining all insights and recommendations."""
    report_id: str
    generated_at: datetime = Field(default_factory=datetime.now)
    
    # Query context
    original_query: str
    analysis_period: Dict[str, str]
    
    # Key findings
    executive_summary: str
    key_insights: List[Insight]
    creative_recommendations: List[CreativeRecommendation]
    
    # Supporting data
    data_summary: DataSummary
    
    # Metadata
    total_hypotheses_tested: int
    validation_success_rate: float
    total_iterations: int = 1
