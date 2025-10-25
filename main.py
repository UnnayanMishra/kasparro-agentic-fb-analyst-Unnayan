"""Main entry point for the agentic Facebook Ads analyst."""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

from workflows.main_workflow import AgenticOrchestrator
from utils.logger import StructuredLogger
from utils.llm_client import ClaudeClient
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Agentic Facebook Ads Analyst - Multi-agent system for ad performance analysis"
    )
    parser.add_argument(
        "query",
        type=str,
        help="Analytical question (e.g., 'Why did ROAS drop last week?')"
    )
    parser.add_argument(
        "--data-file",
        type=str,
        default="data/raw/fb_ads_data.csv",
        help="Path to Facebook Ads data CSV"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports",
        help="Directory for output reports"
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs",
        help="Directory for log files"
    )
    
    args = parser.parse_args()
    
    # Create output directories
    output_dir = Path(args.output_dir)
    log_dir = Path(args.log_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize logger
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"run_{timestamp}.json"
    structured_logger = StructuredLogger(log_file=str(log_file))
    
    logger.info("=" * 60)
    logger.info("KASPARRO AGENTIC FACEBOOK ADS ANALYST")
    logger.info("=" * 60)
    logger.info(f"Query: {args.query}")
    logger.info(f"Data file: {args.data_file}")
    logger.info(f"Output directory: {output_dir}")
    logger.info("=" * 60)
    
    try:
        # Initialize orchestrator
        orchestrator = AgenticOrchestrator(
            llm_client=ClaudeClient(),
            structured_logger=structured_logger,
            max_replans=2
        )
        
        # Execute workflow
        logger.info("Starting multi-agent workflow...")
        final_report = orchestrator.execute(
            query=args.query,
            data_file_path=args.data_file
        )
        
        # Save outputs
        logger.info("Saving outputs...")
        
        # Save insights as JSON
        insights_file = output_dir / "insights.json"
        with open(insights_file, 'w') as f:
            json.dump(
                [insight.model_dump() for insight in final_report.key_insights],
                f,
                indent=2,
                default=str
            )
        logger.info(f"Insights saved to: {insights_file}")
        
        # Save creative recommendations as JSON
        creatives_file = output_dir / "creatives.json"
        with open(creatives_file, 'w') as f:
            json.dump(
                [rec.model_dump() for rec in final_report.creative_recommendations],
                f,
                indent=2,
                default=str
            )
        logger.info(f"Creative recommendations saved to: {creatives_file}")
        
        # Save full report as JSON
        report_json_file = output_dir / "report_full.json"
        with open(report_json_file, 'w') as f:
            json.dump(final_report.model_dump(), f, indent=2, default=str)
        logger.info(f"Full report saved to: {report_json_file}")
        
        # Generate markdown report
        report_md_file = output_dir / "report.md"
        markdown_report = generate_markdown_report(final_report)
        with open(report_md_file, 'w') as f:
            f.write(markdown_report)
        logger.info(f"Markdown report saved to: {report_md_file}")
        
        # Save logs
        structured_logger.save_logs(str(log_file))
        
        logger.info("=" * 60)
        logger.info("WORKFLOW COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        logger.info(f"Total insights: {len(final_report.key_insights)}")
        logger.info(f"Total recommendations: {len(final_report.creative_recommendations)}")
        logger.info(f"Validation success rate: {final_report.validation_success_rate * 100:.1f}%")
        logger.info(f"Total iterations: {final_report.total_iterations}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Workflow failed: {e}", exc_info=True)
        sys.exit(1)


def generate_markdown_report(report) -> str:
    """Generate markdown format report.
    
    Args:
        report: FinalReport object
        
    Returns:
        Markdown formatted report
    """
    md = f"""# Facebook Ads Performance Analysis Report

**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}  
**Report ID:** {report.report_id}  
**Analysis Period:** {report.analysis_period['start']} to {report.analysis_period['end']}

---

## Executive Summary

{report.executive_summary}

**Key Metrics:**
- Total Spend: ${report.data_summary.total_spend:,.2f}
- Total Revenue: ${report.data_summary.total_revenue:,.2f}
- Overall ROAS: {report.data_summary.overall_roas:.2f}
- Hypotheses Tested: {report.total_hypotheses_tested}
- Validation Success Rate: {report.validation_success_rate * 100:.1f}%

---

## Key Insights ({len(report.key_insights)})

"""
    
    for i, insight in enumerate(report.key_insights, 1):
        urgency_emoji = "🔴" if insight.urgency == "critical" else "🟠" if insight.urgency == "high" else "🟡"
        
        md += f"""### {i}. {urgency_emoji} {insight.title}

**Impact Score:** {insight.impact_score}/10  
**Urgency:** {insight.urgency.upper()}  
**Category:** {insight.category}  

**Description:** {insight.description}

**Validation Results:**
- Status: {insight.validation.status}
- Confidence: {insight.validation.confidence_score:.2f}
- Statistical Test: {insight.validation.statistical_test or 'N/A'}
- P-value: {insight.validation.p_value or 'N/A'}

**Verdict:** {insight.validation.verdict}

**Actionability:** {insight.validation.actionability}

---

"""
    
    md += f"""## Creative Recommendations ({len(report.creative_recommendations)})

"""
    
    for i, rec in enumerate(report.creative_recommendations, 1):
        md += f"""### {i}. {rec.action}

**Type:** {rec.recommendation_type}  
**Priority Score:** {rec.priority_score}/10  
**Creative Type:** {rec.creative_type}  
**Target Platform:** {rec.target_platform}

**Data-Driven Rationale:** {rec.data_driven_rationale}

**Expected Improvements:**
"""
        for metric, value in rec.expected_improvement.items():
            md += f"- {metric}: +{value}\n"
        
        if rec.estimated_budget_allocation:
            md += f"\n**Budget Allocation:** ${rec.estimated_budget_allocation:,.2f}\n"
        
        md += "\n---\n\n"
    
    md += """## Methodology

This analysis was conducted using a multi-agent system with the following workflow:

1. **Data Agent**: Loaded and summarized Facebook Ads performance data
2. **Planner Agent**: Decomposed the analytical question into structured tasks
3. **Insight Agent**: Generated testable hypotheses about performance patterns
4. **Evaluator Agent**: Validated hypotheses using statistical tests (t-tests, effect sizes)
5. **Creative Generator Agent**: Produced data-driven creative recommendations

All insights are backed by quantitative evidence with statistical significance testing (p < 0.05) and practical significance (effect size > 0.3).
"""
    
    return md


if __name__ == "__main__":
    main()
