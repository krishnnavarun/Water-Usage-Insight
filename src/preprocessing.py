from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / 'data' / 'raw'
PROCESSED_DIR = ROOT / 'data' / 'processed'


def load_raw_data() -> dict[str, pd.DataFrame]:
    data = {
        'meter': pd.read_csv(RAW_DIR / 'meter.csv'),
        'connections': pd.read_csv(RAW_DIR / 'connections.csv'),
        'billing': pd.read_csv(RAW_DIR / 'billing.csv'),
        'weather': pd.read_csv(RAW_DIR / 'weather.csv'),
        'maintenance': pd.read_csv(RAW_DIR / 'maintenance.csv'),
    }
    return data


def standardize_dataframes(data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    cleaned = data.copy()
    cleaned['meter']['date'] = pd.to_datetime(cleaned['meter']['date'], errors='coerce')
    cleaned['meter']['reading_id'] = cleaned['meter']['reading_id'].astype(str)
    cleaned['meter']['connection_id'] = cleaned['meter']['connection_id'].astype(str)
    cleaned['meter']['usage'] = pd.to_numeric(cleaned['meter']['usage'], errors='coerce')
    cleaned['meter']['meter_status'] = cleaned['meter']['meter_status'].fillna('Normal').astype(str).str.strip()

    cleaned['connections']['connection_id'] = cleaned['connections']['connection_id'].astype(str)
    cleaned['connections']['connection_type'] = cleaned['connections']['connection_type'].astype(str).str.strip().str.title().replace({'Residential ':'Residential','Commercial ':'Commercial'})
    cleaned['connections']['locality'] = cleaned['connections']['locality'].astype(str).str.strip()
    cleaned['connections']['connection_start_date'] = pd.to_datetime(cleaned['connections']['connection_start_date'], errors='coerce')

    cleaned['billing']['billing_id'] = cleaned['billing']['billing_id'].astype(str)
    cleaned['billing']['connection_id'] = cleaned['billing']['connection_id'].astype(str)
    cleaned['billing']['billing_cycle'] = pd.to_datetime(cleaned['billing']['billing_cycle'], format='%Y-%m', errors='coerce').dt.strftime('%Y-%m')
    cleaned['billing']['charge'] = pd.to_numeric(cleaned['billing']['charge'], errors='coerce')

    cleaned['weather']['date'] = pd.to_datetime(cleaned['weather']['date'], errors='coerce')
    cleaned['weather']['locality'] = cleaned['weather']['locality'].astype(str).str.strip()
    cleaned['weather']['temperature'] = pd.to_numeric(cleaned['weather']['temperature'], errors='coerce')
    cleaned['weather']['rain'] = pd.to_numeric(cleaned['weather']['rain'], errors='coerce')

    cleaned['maintenance']['maintenance_id'] = cleaned['maintenance']['maintenance_id'].astype(str)
    cleaned['maintenance']['connection_id'] = cleaned['maintenance']['connection_id'].astype(str)
    cleaned['maintenance']['leak_report'] = pd.to_numeric(cleaned['maintenance']['leak_report'], errors='coerce').fillna(0)
    cleaned['maintenance']['report_date'] = pd.to_datetime(cleaned['maintenance']['report_date'], errors='coerce')
    cleaned['maintenance']['repair_date'] = pd.to_datetime(cleaned['maintenance']['repair_date'], errors='coerce')
    return cleaned


def remove_duplicates(data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    cleaned = data.copy()
    before = cleaned['meter'].shape[0]
    cleaned['meter'] = cleaned['meter'].drop_duplicates(ignore_index=True)
    exact_duplicate_count = before - cleaned['meter'].shape[0]
    duplicate_keys = ['date', 'connection_id']
    duplicate_readings = cleaned['meter'].duplicated(subset=duplicate_keys, keep=False)
    dup_df = cleaned['meter'][duplicate_readings].sort_values(['connection_id', 'date'])
    cleaned['meter'] = cleaned['meter'].drop_duplicates(subset=duplicate_keys, keep='first').reset_index(drop=True)
    cleaned['meter']['duplicate_reading_flag'] = cleaned['meter'].duplicated(subset=['date', 'connection_id'], keep=False)
    return cleaned, {'exact_duplicates_removed': exact_duplicate_count, 'duplicate_meter_readings': dup_df}


def flag_invalid_usage(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    df = df.copy()
    summary = {
        'negative_usage': int((df['usage'] < 0).sum()),
        'extreme_usage': int((df['usage'] > df['usage'].quantile(0.99) * 2).sum()),
        'missing_usage': int(df['usage'].isna().sum()),
    }
    df['invalid_usage_flag'] = df['usage'] < 0
    df.loc[df['usage'] < 0, 'usage'] = np.nan
    df['usage_outlier_flag'] = df['usage'] > df['usage'].quantile(0.99) * 2
    df['usage_outlier_flag'] = df['usage_outlier_flag'].fillna(False)
    return df, summary


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['usage'] = df.groupby('connection_id')['usage'].transform(lambda s: s.fillna(s.median()))
    df['meter_status'] = df['meter_status'].fillna('Normal')
    return df


def merge_analysis_tables(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    meter = data['meter'].copy()
    connections = data['connections'].copy()
    weather = data['weather'].copy()
    billing = data['billing'].copy()
    maintenance = data['maintenance'].copy()

    meter = meter.merge(connections, on='connection_id', how='left')
    meter['date_month'] = meter['date'].dt.to_period('M').astype(str)
    billing = billing.rename(columns={'billing_cycle': 'date_month'})
    meter = meter.merge(billing[['connection_id', 'date_month', 'charge']], on=['connection_id', 'date_month'], how='left')

    weather = weather.rename(columns={'date': 'date'})
    meter = meter.merge(weather, on=['date', 'locality'], how='left', validate='many_to_one')

    maintenance_daily = []
    for _, row in maintenance.iterrows():
        if pd.isna(row['report_date']):
            continue
        active_dates = pd.date_range(row['report_date'], row['repair_date'] if pd.notna(row['repair_date']) else row['report_date'], freq='D')
        for d in active_dates:
            maintenance_daily.append({'connection_id': row['connection_id'], 'date': d, 'leak_report': int(row['leak_report']), 'repair_date': row['repair_date']})
    maintenance_daily = pd.DataFrame(maintenance_daily)
    if not maintenance_daily.empty:
        maintenance_daily['date'] = pd.to_datetime(maintenance_daily['date'])
        maintenance_daily = maintenance_daily.drop_duplicates(subset=['connection_id', 'date'])
        meter = meter.merge(maintenance_daily, on=['connection_id', 'date'], how='left', validate='many_to_one')
    else:
        meter['leak_report'] = 0
        meter['repair_date'] = pd.NaT

    meter['leak_report'] = meter['leak_report'].fillna(0).astype(int)
    meter['days_since_repair'] = (meter['date'] - pd.to_datetime(meter['repair_date'])).dt.days if 'repair_date' in meter.columns else np.nan
    meter['days_since_repair'] = pd.to_numeric(meter['days_since_repair'], errors='coerce')
    meter['is_repair_period'] = meter['days_since_repair'].between(0, 14)
    meter['anomaly_label'] = (
        (meter['usage'] > meter['usage'].quantile(0.99) * 1.5) |
        (meter['leak_report'] == 1) |
        (meter['usage'] < 0)
    ).astype(int)
    meter = meter.sort_values('date').reset_index(drop=True)
    return meter


def create_processed_dataset() -> pd.DataFrame:
    data = load_raw_data()
    data = standardize_dataframes(data)
    data, duplicate_summary = remove_duplicates(data)
    data['meter'], invalid_summary = flag_invalid_usage(data['meter'])
    data['meter'] = handle_missing_values(data['meter'])
    processed = merge_analysis_tables(data)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    processed.to_csv(PROCESSED_DIR / 'analysis_ready.csv', index=False)
    duplicate_summary['duplicate_meter_readings'] = int(len(duplicate_summary['duplicate_meter_readings']))
    with open(PROCESSED_DIR / 'data_quality_summary.json', 'w', encoding='utf-8') as f:
        json.dump({
            'duplicate_summary': duplicate_summary,
            'invalid_usage_summary': invalid_summary,
        }, f, indent=2)
    return processed


if __name__ == '__main__':
    create_processed_dataset()
    print('Processed dataset saved to', PROCESSED_DIR)
