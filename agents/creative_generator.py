"""Creative Generator Agent - Produces data-driven recommendations."""

from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from prompts.creative_prompts import CREATIVE_GENERATOR_SYSTEM_PROMPT, format_creative_generator_prompt
from utils.validators import CreativeAnalysis, CreativeRecommendation, Insight
from utils.data_processors import load_fb_ads_data, get_performance_by_dimension
from pydantic import ValidationError
from datetime import datetime


class CreativeGeneratorAgent(BaseAgent):
    """Agent that generates creative recommendations."""
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_name="CreativeGeneratorAgent",
            system_prompt=CREATIVE_GENERATOR_SYSTEM_PROMPT,
            **kwargs
        )
    
    def execute(
        self,
        validated_insights: List[Insight],
        data_file_path: str = "data/raw/fb_ads_data.csv"
    ) -> CreativeAnalysis:
        """Generate creative recommendations from validated insights.
        
        Args:
            validated_insights: List of validated insights
            data_file_path: Path to data file
            
        Returns:
            CreativeAnalysis with recommendations
        """
        self._log_event("creative_generation_start", {
            "num_insights": len(validated_insights)
        })
        
        # Load data for analysis
        df = load_fb_ads_data(data_file_path)
        
        # Analyze creative performance
        creative_perf = get_performance_by_dimension(df, 'creative_type')
        platform_perf = get_performance_by_dimension(df, 'platform')
        
        # Get top and bottom performers
        top_performers = self._get_top_performers(df)
        underperformers = self._get_underperformers(df)
        
        # Identify patterns
        winning_patterns = self._identify_patterns(df, top_performers)
        losing_patterns = self._identify_patterns(df, underperformers, winning=False)
        
        # Prepare context for LLM
        performance_summary = {
            "creative_type": creative_perf.to_dict('index'),
            "platform": platform_perf.to_dict('index')
        }
        
        budget_info = {
            "total_spend": df['spend'].sum(),
            "by_creative_type": df.groupby('creative_type')['spend'].sum().to_dict()
        }
        
        # Format prompt
        user_prompt = format_creative_generator_prompt(
            validated_insights=[i.model_dump() for i in validated_insights],
            performance_summary=performance_summary,
            creative_breakdown=creative_perf.to_dict('index'),
            budget_info=budget_info
        )
        
        # Call LLM
        response = self._call_llm(user_prompt)
        
        # Parse response
        analysis_dict = self._parse_json_response(response)
        
        # Validate structure
        self._validate_output(analysis_dict, ["recommendations"])
        
        # Convert to Pydantic model
        try:
            recommendations = [
                CreativeRecommendation(**rec)
                for rec in analysis_dict["recommendations"]
            ]
            
            creative_analysis = CreativeAnalysis(
                analysis_date=datetime.now(),
                top_performing_creatives=top_performers,
                underperforming_creatives=underperformers,
                winning_patterns=winning_patterns,
                losing_patterns=losing_patterns,
                recommendations=recommendations,
                overall_creative_performance={
                    "avg_roas_by_type": creative_perf['roas'].to_dict(),
                    "best_performing_segment": self._get_best_segment(df),
                    "creative_fatigue_detected": self._detect_fatigue(df)
                }
            )
            
            self._log_event("creative_generation_success", {
                "num_recommendations": len(recommendations),
                "avg_priority": sum(r.priority_score for r in recommendations) / len(recommendations)
            })
            
            return creative_analysis
            
        except ValidationError as e:
            self._log_event("validation_error", {"error": str(e)}, status="error")
            raise ValueError(f"Creative analysis validation failed: {e}")
    
    def _get_top_performers(self, df, top_n: int = 5) -> List[Dict[str, Any]]:
        """Get top performing creatives.
        
        Args:
            df: Dataset
            top_n: Number of top performers
            
        Returns:
            List of top performer details
        """
        # Group by creative attributes and calculate ROAS
        grouped = df.groupby(['creative_type', 'platform', 'creative_message']).agg({
            'roas': 'mean',
            'spend': 'sum',
            'revenue': 'sum',
            'ctr': 'mean'
        }).reset_index()
        
        # Sort by ROAS and get top N
        top = grouped.nlargest(top_n, 'roas')
        
        return [
            {
                "creative_type": row['creative_type'],
                "platform": row['platform'],
                "message_preview": row['creative_message'][:50] + "...",
                "roas": round(row['roas'], 2),
                "spend": round(row['spend'], 2),
                "ctr": round(row['ctr'], 3)
            }
            for _, row in top.iterrows()
        ]
    
    def _get_underperformers(self, df, bottom_n: int = 5) -> List[Dict[str, Any]]:
        """Get underperforming creatives.
        
        Args:
            df: Dataset
            bottom_n: Number of bottom performers
            
        Returns:
            List of underperformer details
        """
        grouped = df.groupby(['creative_type', 'platform', 'creative_message']).agg({
            'roas': 'mean',
            'spend': 'sum',
            'revenue': 'sum',
            'ctr': 'mean'
        }).reset_index()
        
        # Filter for significant spend (>1% of total)
        total_spend = df['spend'].sum()
        grouped = grouped[grouped['spend'] > total_spend * 0.01]
        
        # Sort by ROAS and get bottom N
        bottom = grouped.nsmallest(bottom_n, 'roas')
        
        return [
            {
                "creative_type": row['creative_type'],
                "platform": row['platform'],
                "message_preview": row['creative_message'][:50] + "...",
                "roas": round(row['roas'], 2),
                "spend": round(row['spend'], 2),
                "ctr": round(row['ctr'], 3)
            }
            for _, row in bottom.iterrows()
        ]
    
    def _identify_patterns(
        self,
        df,
        examples: List[Dict],
        winning: bool = True
    ) -> List[str]:
        """Identify patterns in creative performance.
        
        Args:
            df: Dataset
            examples: List of example creatives
            winning: Whether these are winning patterns
            
        Returns:
            List of pattern descriptions
        """
        patterns = []
        
        if not examples:
            return patterns
        
        # Analyze creative type distribution
        creative_types = [e['creative_type'] for e in examples]
        if len(set(creative_types)) < len(creative_types):
            most_common = max(set(creative_types), key=creative_types.count)
            patterns.append(
                f"{'Best' if winning else 'Worst'} performers dominated by {most_common} format"
            )
        
        # Analyze platform distribution
        platforms = [e['platform'] for e in examples]
        if len(set(platforms)) < len(platforms):
            most_common = max(set(platforms), key=platforms.count)
            patterns.append(
                f"{most_common} shows {'stronger' if winning else 'weaker'} performance in this set"
            )
        
        return patterns
    
    def _get_best_segment(self, df) -> str:
        """Identify best performing segment.
        
        Args:
            df: Dataset
            
        Returns:
            Description of best segment
        """
        # Find combination with highest ROAS
        grouped = df.groupby(['creative_type', 'platform']).agg({
            'roas': 'mean',
            'spend': 'sum'
        }).reset_index()
        
        # Filter for significant spend
        grouped = grouped[grouped['spend'] > df['spend'].sum() * 0.05]
        
        best = grouped.loc[grouped['roas'].idxmax()]
        
        return f"{best['creative_type']} on {best['platform']}"
    
    def _detect_fatigue(self, df) -> bool:
        """Detect creative fatigue.
        
        Args:
            df: Dataset
            
        Returns:
            True if fatigue detected
        """
        # Sort by date and calculate rolling CTR
        df_sorted = df.sort_values('date')
        
        # Compare first and last week CTR
        first_week = df_sorted.head(7)['ctr'].mean()
        last_week = df_sorted.tail(7)['ctr'].mean()
        
        # Fatigue if CTR dropped more than 20%
        return last_week < first_week * 0.8
