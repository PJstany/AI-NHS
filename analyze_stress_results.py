#!/usr/bin/env python3
"""
Quick analysis of stress test results to show the impact of bias fixes and increased utilization
"""
import pandas as pd
import numpy as np

# Load results
df = pd.read_csv('outputs/aggregate_overall.csv')

# Group by utilization and subgroup
summary = df.groupby(['utilization', 'subgroup']).agg({
    'mean_wait': ['mean', 'std'],
    'P95': ['mean', 'max'],
    'urgent_breach_rate': ['mean', 'max'],
    'same_day_rate': ['mean', 'min'],
    'within_3d_rate': ['mean', 'min']
}).round(4)

print("=== STRESS TEST RESULTS SUMMARY ===\n")
print("Key Findings:")
print("1. BIAS IMPACT: Group B consistently has higher wait times")
print("2. UTILIZATION STRESS: Higher utilization = worse outcomes")
print("3. TAIL RISKS: P95 wait times show extreme cases\n")

print("Mean Wait Times by Group and Utilization:")
wait_pivot = df.pivot_table(values='mean_wait', index='utilization', columns='subgroup', aggfunc='mean')
print(wait_pivot.round(4))

print("\nP95 Wait Times (showing tail risks):")
p95_pivot = df.pivot_table(values='P95', index='utilization', columns='subgroup', aggfunc='max')
print(p95_pivot.round(2))

print("\nSame-Day Access Rates (higher is better):")
access_pivot = df.pivot_table(values='same_day_rate', index='utilization', columns='subgroup', aggfunc='mean')
print(access_pivot.round(4))

print("\nUrgent Breach Rates (lower is better):")
breach_pivot = df.pivot_table(values='urgent_breach_rate', index='utilization', columns='subgroup', aggfunc='mean')
print(breach_pivot.round(4))

# Calculate equity gaps
print("\n=== EQUITY ANALYSIS ===")
for util in sorted(df['utilization'].unique()):
    util_data = df[df['utilization'] == util]
    a_wait = util_data[util_data['subgroup'] == 'A']['mean_wait'].mean()
    b_wait = util_data[util_data['subgroup'] == 'B']['mean_wait'].mean()
    gap = b_wait - a_wait
    print(f"Utilization {util}: Group B waits {gap:.4f} days longer on average ({gap*24:.1f} hours)")

print("\n=== SYSTEM STRESS INDICATORS ===")
for util in sorted(df['utilization'].unique()):
    util_data = df[df['utilization'] == util]
    max_p95 = util_data['P95'].max()
    min_access = util_data['same_day_rate'].min()
    max_breach = util_data['urgent_breach_rate'].max()
    print(f"Utilization {util}: Max P95={max_p95:.1f} days, Min same-day access={min_access:.3f}, Max urgent breach={max_breach:.4f}")