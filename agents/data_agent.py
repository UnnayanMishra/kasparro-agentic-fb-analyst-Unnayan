"""Data Agent - Loads and summarizes Facebook Ads data."""

from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from prompts.data_prompts import DATA_AGENT_SYSTEM_PROMPT, format_data_agent_prompt
from utils.validators import DataSummary
from utils.data_processors import (
    load_fb_ads_data,
    calculate_metrics,
    get_performance_by_dimension
)
from pydantic import ValidationError
import json


class DataAgent(BaseAgent):
    """Agent that loads and analyzes data."""
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_name="DataAgent",
            system_prompt=DATA_AGENT_SYSTEM_PROMPT,
            **kwargs
        )
    
    def execute(
        self,
        data_file_path: str = "data/raw/fb_ads_data.csv",
        focus_areas: List[str] = None
    ) -> DataSummary:
        """Load and summarize the dataset.
        
        Args:
            data_file_path: Path to CSV file
            focus_areas: Specific areas to focus on
            
        Returns:
            DataSummary object with key metrics
        """
        self._log_event("data_load_start", {"file": data_file_path})
        
        # Load actual data
        df = load_fb_ads_data(data_file_path)
        
        # Calculate metrics
        metrics = calculate_metrics(df)
        
        # Get dimensional breakdowns
        creative_perf = get_performance_by_dimension(df, 'creative_type').to_dict('index')
        platform_perf = get_performance_by_dimension(df, 'platform').to_dict('index')
        country_perf = get_performance_by_dimension(df, 'country').to_dict('index')
        
        # Get unique campaigns
        campaigns = df['campaign_name'].unique().tolist()
        
        # Detect anomalies
        anomalies = self._detect_anomalies(df)
        
        # Create DataSummary
        data_summary = DataSummary(
            total_rows=len(df),
            date_range=metrics['date_range'],
            campaigns=campaigns,
            total_spend=metrics['total_spend'],
            total_revenue=metrics['total_revenue'],
            overall_roas=metrics['overall_roas'],
            performance_by_creative_type=creative_perf,
            performance_by_platform=platform_perf,
            performance_by_country=country_perf,
            anomalies=anomalies
        )
        
        self._log_event("data_load_success", {
            "rows": len(df),
            "campaigns": len(campaigns),
            "anomalies_found": len(anomalies)
        })
        
        return data_summary
    
    def _detect_anomalies(self, df) -> List[str]:
        """Detect performance anomalies in the data.
        
        Args:
            df: Facebook Ads dataframe
            
        Returns:
            List of anomaly descriptions
        """
        anomalies = []
        
        # Check for ROAS drops
        df_sorted = df.sort_values('date')
        recent_roas = df_sorted.tail(7)['roas'].mean()
        previous_roas = df_sorted.head(7)['roas'].mean()
        
        if recent_roas < previous_roas * 0.8:
            anomalies.append(
                f"ROAS dropped {((previous_roas - recent_roas) / previous_roas * 100):.1f}% "
                f"in recent 7 days ({previous_roas:.2f} → {recent_roas:.2f})"
            )
        
        # Check for CTR drops
        recent_ctr = df_sorted.tail(7)['ctr'].mean()
        previous_ctr = df_sorted.head(7)['ctr'].mean()
        
        if recent_ctr < previous_ctr * 0.85:
            anomalies.append(
                f"CTR declined {((previous_ctr - recent_ctr) / previous_ctr * 100):.1f}% "
                f"in recent period ({previous_ctr:.2f}% → {recent_ctr:.2f}%)"
            )
        
        # Check for high spend segments with low ROAS
        for creative_type in df['creative_type'].unique():
            subset = df[df['creative_type'] == creative_type]
            if subset['roas'].mean() < 3.0 and subset['spend'].sum() > df['spend'].sum() * 0.15:
                anomalies.append(
                    f"{creative_type} creatives consuming {(subset['spend'].sum() / df['spend'].sum() * 100):.1f}% "
                    f"of budget but ROAS only {subset['roas'].mean():.2f}"
                )
        
        return anomalies
