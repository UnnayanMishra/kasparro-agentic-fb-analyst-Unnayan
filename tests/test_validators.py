"""Test Pydantic schemas."""

import pytest
from utils.validators import (
    Hypothesis, ValidationResult, Insight, CreativeRecommendation,
    ConfidenceLevel, HypothesisStatus, CreativeType, Platform
)


def test_hypothesis_creation():
    """Test creating a hypothesis."""
    hyp = Hypothesis(
        hypothesis_id="hyp_001",
        statement="Image creatives outperform Video on Facebook",
        rationale="Historical data shows higher ROAS for Image format",
        metric_to_test="roas",
        expected_direction="increase",
        segment_dimension="creative_type",
        segment_value="Image",
        confidence="high",
        supporting_evidence=["Previous 30-day data", "Industry benchmarks"]
    )
    
    assert hyp.hypothesis_id == "hyp_001"
    assert hyp.confidence == "high"
    assert len(hyp.supporting_evidence) == 2


def test_validation_result():
    """Test validation result with confidence score."""
    validation = ValidationResult(
        hypothesis_id="hyp_001",
        status="validated",
        confidence_score=0.85,
        statistical_test="t-test",
        p_value=0.02,
        effect_size=1.3,
        supporting_metrics={"roas_lift": 0.8, "sample_size": 450},
        verdict="Hypothesis validated with high confidence",
        actionability="Scale Image creatives on Facebook immediately"
    )
    
    assert validation.confidence_score == 0.85
    assert validation.status == "validated"
    assert validation.p_value < 0.05


def test_creative_recommendation():
    """Test creative recommendation model."""
    rec = CreativeRecommendation(
        recommendation_id="rec_001",
        recommendation_type="scale_creative",
        action="Increase budget for Image creatives on Facebook by 30%",
        creative_type="Image",
        target_platform="Facebook",
        data_driven_rationale="Image creatives show 6.13 ROAS vs 5.35 for Video",
        expected_improvement={"roas": 0.78, "revenue": 15000},
        priority_score=9.2,
        reference_examples=["ad_12345", "ad_67890"]
    )
    
    assert rec.priority_score == 9.2
    assert rec.creative_type == "Image"


def test_confidence_validation():
    """Test that confidence score must be between 0 and 1."""
    with pytest.raises(ValueError):
        ValidationResult(
            hypothesis_id="hyp_001",
            status="validated",
            confidence_score=1.5,  # Invalid - too high
            verdict="Test",
            actionability="Test"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
