"""
Regenerate data.json from source CSVs.
Run when refreshing the dashboard with new iehr extraction output.

Inputs (expected in same directory or specified path):
  iadmin_lso100_days_to_cert.csv
  iadmin_lso200_days_to_cert.csv
  iadmin_lso300_days_to_cert.csv
  iadmin_lso400_days_to_cert.csv
  iadmin_lso_all_levels_combined.csv

Output:
  data.json

Usage:
  python3 build_data.py [--source-dir /path/to/csvs] [--output data.json]
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('--source-dir', default='.', help='Directory containing the source CSVs')
parser.add_argument('--output', default='data.json', help='Output JSON path')
args = parser.parse_args()

src = Path(args.source_dir)
out = Path(args.output)

required = ['iadmin_lso100_days_to_cert.csv', 'iadmin_lso200_days_to_cert.csv',
            'iadmin_lso300_days_to_cert.csv', 'iadmin_lso400_days_to_cert.csv',
            'iadmin_lso_all_levels_combined.csv']
missing = [f for f in required if not (src / f).exists()]
if missing:
    print(f'Missing required files in {src}: {missing}', file=sys.stderr)
    sys.exit(1)

df_all = pd.read_csv(src / 'iadmin_lso_all_levels_combined.csv', encoding='utf-8-sig')
df100 = pd.read_csv(src / 'iadmin_lso100_days_to_cert.csv', encoding='utf-8-sig')
df200 = pd.read_csv(src / 'iadmin_lso200_days_to_cert.csv', encoding='utf-8-sig')
df300 = pd.read_csv(src / 'iadmin_lso300_days_to_cert.csv', encoding='utf-8-sig')
df400 = pd.read_csv(src / 'iadmin_lso400_days_to_cert.csv', encoding='utf-8-sig')

for df in [df_all, df100, df200, df300, df400]:
    df['lso_acquired_date'] = df['lso_acquired_date'].astype(str).str.split(' ').str[0]
    df['days_to_cert'] = df['days_to_cert'].astype(int)
    for col in ['hire_date', 'dept_name', 'current_position_name', 'email']:
        df[col] = df[col].fillna('').astype(str)

def stats_for(df):
    d = df['days_to_cert']
    sep = (df['employee_status'] == 'Separated').sum()
    return {
        'total': len(df), 'active': int((df['employee_status'] == 'Active').sum()), 'separated': int(sep),
        'attrition': round(sep / len(df) * 100, 1),
        'min': int(d.min()), 'p5': int(d.quantile(0.05)), 'p25': int(d.quantile(0.25)),
        'median': int(d.median()), 'p75': int(d.quantile(0.75)), 'p95': int(d.quantile(0.95)),
        'max': int(d.max()), 'mean': round(d.mean(), 1),
        'anomaly': int((df['data_anomaly'] == 'Y').sum()),
    }

per_level = {f'LSO{l}': stats_for(df) for l, df in [(100, df100), (200, df200), (300, df300), (400, df400)]}

# Full pipeline cohort
pipe = df_all.groupby('employee_no')['cert_level'].apply(set).reset_index()
pipe['level_count'] = pipe['cert_level'].apply(len)
full_pipe_emps = pipe[pipe['level_count'] == 4]['employee_no'].tolist()
fp = df_all[df_all['employee_no'].isin(full_pipe_emps)].pivot_table(
    index='employee_no', columns='cert_level', values='days_to_cert', aggfunc='first'
).reset_index()
emp_meta = df_all[['employee_no', 'full_name', 'hire_date', 'dept_name', 'current_position_name', 'employee_status']].drop_duplicates('employee_no')
fp = fp.merge(emp_meta, on='employee_no', how='left')
fp['d100_200'] = fp['LSO200'] - fp['LSO100']
fp['d200_300'] = fp['LSO300'] - fp['LSO200']
fp['d300_400'] = fp['LSO400'] - fp['LSO300']
fp = fp.sort_values('LSO400').to_dict('records')

# Patterns
pipe['pattern'] = pipe['cert_level'].apply(lambda s: ''.join(['1' if f'LSO{l}' in s else '0' for l in [100, 200, 300, 400]]))
patterns = pipe['pattern'].value_counts().to_dict()

# Dept dist
dept_dist = df_all.pivot_table(index='dept_name', columns='cert_level', values='employee_no', aggfunc='count', fill_value=0).reset_index()
dept_dist['total'] = dept_dist[['LSO100', 'LSO200', 'LSO300', 'LSO400']].sum(axis=1)
dept_dist = dept_dist.sort_values('total', ascending=False).head(20).to_dict('records')

# Position dist
pos_dist = df_all.pivot_table(index='current_position_name', columns='cert_level', values='employee_no', aggfunc='count', fill_value=0).reset_index()
pos_dist['total'] = pos_dist[['LSO100', 'LSO200', 'LSO300', 'LSO400']].sum(axis=1)
pos_dist = pos_dist.sort_values('total', ascending=False).to_dict('records')

# Anomalies
anomalies = df_all[df_all['data_anomaly'] == 'Y'].to_dict('records')

# Slowest / fastest per level
slowest = {}
fastest = {}
for name, df in [('LSO100', df100), ('LSO200', df200), ('LSO300', df300), ('LSO400', df400)]:
    slowest[name] = df.nlargest(5, 'days_to_cert').to_dict('records')
    pos = df[df['days_to_cert'] > 0]
    fastest[name] = pos.nsmallest(5, 'days_to_cert').to_dict('records')

# Histograms
def histogram(d, bins=[-200, -100, -30, 0, 30, 60, 90, 120, 150, 180, 210, 240, 280]):
    return {'bins': bins, 'counts': [int(((d >= bins[i]) & (d < bins[i+1])).sum()) for i in range(len(bins)-1)]}

histograms = {f'LSO{l}': histogram(df['days_to_cert']) for l, df in [(100, df100), (200, df200), (300, df300), (400, df400)]}

# All records sorted
records = df_all.sort_values(['cert_level', 'lso_acquired_date']).to_dict('records')

# Clean NaN from store_id everywhere
def clean(records):
    for r in records:
        for k, v in list(r.items()):
            if isinstance(v, float) and v != v:  # NaN check
                r[k] = ''
    return records
records = clean(records); anomalies = clean(anomalies); fp = clean(fp)
for lvl in slowest: slowest[lvl] = clean(slowest[lvl]); fastest[lvl] = clean(fastest[lvl])

data = {
    'meta': {
        'report_id': 'LCNA-HR-LSO-2026-003',
        'window': '2025-05-27 → 2026-05-27',
        'generated': pd.Timestamp.now().strftime('%Y-%m-%d'),
        'data_source': 'iehr.luckyus_iehr.* via MCP DB Gateway',
        'tenant': 'LKUS',
        'total_records': len(df_all),
        'total_emps': len(pipe),
        'full_pipeline_emps': len(fp),
    },
    'per_level': per_level,
    'patterns': patterns,
    'histograms': histograms,
    'dept_dist': dept_dist,
    'pos_dist': pos_dist,
    'full_pipeline': fp,
    'anomalies': anomalies,
    'slowest': slowest,
    'fastest': fastest,
    'records': records,
}

with open(out, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, default=str, separators=(',', ':'))

print(f'Wrote {out} ({out.stat().st_size:,} bytes)')
print(f'  total_records={len(df_all)}, distinct_emps={len(pipe)}, full_pipeline={len(fp)}, anomalies={len(anomalies)}')
