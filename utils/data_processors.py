"""Data processing utilities for Facebook Ads data."""

import pandas as pd
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def load_fb_ads_data(file_path: str = "data/raw/fb_ads_data.csv") -> pd.DataFrame:
    """Load Facebook Ads data from CSV.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        Cleaned pandas DataFrame
    """
    try:
        df = pd.read_csv(file_path)
        
        # Clean column names (strip whitespace)
        df.columns = df.columns.str.strip()
        
        # Convert date to datetime - use mixed format to handle variations
        df['date'] = pd.to_datetime(df['date'], format='mixed', dayfirst=False)
        
        # Sort by date
        df = df.sort_values('date').reset_index(drop=True)
        
        # Calculate derived metrics if not present
        if 'cpc' not in df.columns:
            df['cpc'] = df['spend'] / df['clicks'].replace(0, 1)  # Avoid division by zero
        
        logger.info(f"Loaded {len(df)} rows from {file_path}")
        logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
        
        return df
        
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        raise


def calculate_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate summary metrics from dataframe.
    
    Args:
        df: Facebook Ads dataframe
        
    Returns:
        Dictionary of summary metrics
    """
    total_clicks = df['clicks'].sum()
    
    return {
        "total_spend": round(df['spend'].sum(), 2),
        "total_revenue": round(df['revenue'].sum(), 2),
        "overall_roas": round(df['revenue'].sum() / df['spend'].sum(), 2),
        "avg_ctr": round(df['ctr'].mean() * 100, 2),  # Convert to percentage
        "total_purchases": int(df['purchases'].sum()),
        "avg_cpc": round(df['spend'].sum() / total_clicks, 3) if total_clicks > 0 else 0,
        "total_impressions": int(df['impressions'].sum()),
        "total_clicks": int(total_clicks),
        "date_range": {
            "start": df['date'].min().strftime('%Y-%m-%d'),
            "end": df['date'].max().strftime('%Y-%m-%d'),
            "days": (df['date'].max() - df['date'].min()).days + 1
        }
    }


def get_performance_by_dimension(
    df: pd.DataFrame, 
    dimension: str
) -> pd.DataFrame:
    """Aggregate performance by a specific dimension.
    
    Args:
        df: Facebook Ads dataframe
        dimension: Column to group by (e.g., 'creative_type', 'platform')
        
    Returns:
        Aggregated dataframe
    """
    agg_df = df.groupby(dimension).agg({
        'spend': 'sum',
        'revenue': 'sum',
        'impressions': 'sum',
        'clicks': 'sum',
        'purchases': 'sum'
    }).assign(
        roas=lambda x: x['revenue'] / x['spend'],
        ctr=lambda x: (x['clicks'] / x['impressions']) * 100,  # As percentage
        cpc=lambda x: x['spend'] / x['clicks']
    ).round(3)
    
    # Sort by revenue descending
    return agg_df.sort_values('revenue', ascending=False)


def get_time_series_metrics(df: pd.DataFrame, freq: str = 'D') -> pd.DataFrame:
    """Get time series of key metrics.
    
    Args:
        df: Facebook Ads dataframe
        freq: Frequency for resampling ('D'=daily, 'W'=weekly)
        
    Returns:
        Time series dataframe
    """
    df_ts = df.set_index('date').resample(freq).agg({
        'spend': 'sum',
        'revenue': 'sum',
        'impressions': 'sum',
        'clicks': 'sum',
        'purchases': 'sum'
    })
    
    df_ts['roas'] = (df_ts['revenue'] / df_ts['spend']).round(2)
    df_ts['ctr'] = ((df_ts['clicks'] / df_ts['impressions']) * 100).round(3)
    
    return df_ts
