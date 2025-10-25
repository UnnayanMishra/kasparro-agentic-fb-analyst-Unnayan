"""Quick data analysis script."""

import sys
sys.path.append('.')

from utils.data_processors import load_fb_ads_data, calculate_metrics, get_performance_by_dimension

# Load data
df = load_fb_ads_data()

print("=" * 60)
print("DATA OVERVIEW")
print("=" * 60)
print(f"Total rows: {len(df)}")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")
print(f"Columns: {list(df.columns)}")

print("\n" + "=" * 60)
print("SUMMARY METRICS")
print("=" * 60)
metrics = calculate_metrics(df)
for key, value in metrics.items():
    print(f"{key}: {value}")

print("\n" + "=" * 60)
print("PERFORMANCE BY CREATIVE TYPE")
print("=" * 60)
print(get_performance_by_dimension(df, 'creative_type'))

print("\n" + "=" * 60)
print("PERFORMANCE BY PLATFORM")
print("=" * 60)
print(get_performance_by_dimension(df, 'platform'))

print("\n" + "=" * 60)
print("PERFORMANCE BY COUNTRY")
print("=" * 60)
print(get_performance_by_dimension(df, 'country'))
