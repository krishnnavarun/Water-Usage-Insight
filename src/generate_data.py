from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd


SEED = 42
RAW_DIR = Path(__file__).resolve().parents[1] / 'data' / 'raw'


def generate_synthetic_data() -> None:
    np.random.seed(SEED)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    start_date = pd.Timestamp('2023-01-01')
    end_date = pd.Timestamp('2024-12-31')
    all_dates = pd.date_range(start_date, end_date, freq='D')
    localities = ['North Ridge', 'Downtown', 'Harbor View', 'Rivergate', 'Old Town', 'Lakewood']

    connection_id_map = []
    connection_rows = []
    billing_rows = []
    weather_rows = []
    maintenance_rows = []

    connection_count = 96
    residential_count = 66
    commercial_count = connection_count - residential_count
    res_type_values = ['Residential', 'residential', ' RESIDENTIAL ', 'Residential']
    comm_type_values = ['Commercial', 'commercial', 'COMMERCIAL', 'Commercial']

    for idx in range(1, connection_count + 1):
        cid = f'C-{idx:03d}'
        conn_type = 'Residential' if idx <= residential_count else 'Commercial'
        locality = localities[(idx - 1) % len(localities)]
        household_size = np.random.choice(['1-2', '3-4', '5+'], p=[0.25, 0.5, 0.25]) if conn_type == 'Residential' else 'Commercial'
        start = pd.Timestamp(np.random.randint(2016, 2023))
        start += pd.to_timedelta(np.random.randint(0, 364), unit='D')
        connection_rows.append({
            'connection_id': cid,
            'connection_type': conn_type,
            'locality': locality,
            'household_size_band': household_size,
            'connection_start_date': start.strftime('%Y-%m-%d'),
        })

        for month_idx in range(1, 25):
            cycle = pd.Timestamp(f'2023-01-01') + pd.DateOffset(months=month_idx - 1)
            base_charge = 60 if conn_type == 'Residential' else 220
            seasonal = 1 + 0.18 * np.sin((month_idx / 12) * 2 * np.pi)
            charge = round(base_charge * seasonal + np.random.uniform(10, 60), 2)
            billing_rows.append({
                'billing_id': f'B-{cid}-{month_idx:02d}',
                'connection_id': cid,
                'billing_cycle': cycle.strftime('%Y-%m'),
                'charge': charge,
            })

    connection_df = pd.DataFrame(connection_rows)
    connection_df.loc[connection_df.index % 17 == 0, 'connection_type'] = 'commercial'
    connection_df.loc[connection_df.index % 23 == 0, 'connection_type'] = ' RESIDENTIAL '
    connection_df['connection_type'] = connection_df['connection_type'].str.strip().str.title()

    for locality in localities:
        local_temp = 18 + 12 * np.sin(np.linspace(0, 2 * np.pi, len(all_dates))) + np.random.normal(0, 2.5, len(all_dates))
        local_rain = np.maximum(0, 30 + 25 * np.sin(np.linspace(0, 2 * np.pi, len(all_dates)) + 1.1) + np.random.normal(0, 8, len(all_dates)))
        for d, temp, rain in zip(all_dates, local_temp, local_rain):
            weather_rows.append({
                'date': d.strftime('%Y-%m-%d'),
                'locality': locality,
                'temperature': round(float(temp), 2),
                'rain': round(float(rain), 2),
            })

    weather_df = pd.DataFrame(weather_rows)

    meter_rows = []
    true_anomaly_ids = set()
    for _, row in connection_df.iterrows():
        cid = row['connection_id']
        locality = row['locality']
        conn_type = row['connection_type']
        base_usage = 110 if conn_type == 'Residential' else 350
        mobility = 25 if conn_type == 'Residential' else 90
        for date in all_dates:
            weather_match = weather_df[(weather_df['date'] == date.strftime('%Y-%m-%d')) & (weather_df['locality'] == locality)].iloc[0]
            temp = weather_match['temperature']
            rain = weather_match['rain']
            seasonal = 1 + 0.4 * np.sin((date.dayofyear / 365) * 2 * np.pi)
            weekend_factor = 1.12 if date.dayofweek >= 5 else 1.0
            weather_factor = 1 + (temp - 20) * 0.015 - (rain / 100) * 0.15
            profile = 1.0 + (0.08 if conn_type == 'Residential' else 0.15) * np.random.normal(0, 1)
            usage = base_usage * seasonal * weekend_factor * weather_factor * profile + np.random.normal(0, 18)
            if np.random.rand() < 0.0025:
                usage += 100
                true_anomaly_ids.add(f'{cid}|{date.strftime("%Y-%m-%d")}')
            usage = max(usage, 0)
            meter_rows.append({
                'reading_id': f'R-{cid}-{date.strftime("%Y%m%d")}',
                'date': date.strftime('%Y-%m-%d'),
                'connection_id': cid,
                'usage': float(round(usage, 2)),
                'meter_status': 'Normal' if np.random.rand() > 0.03 else 'Estimated',
            })

    meter_df = pd.DataFrame(meter_rows)
    for _ in range(25):
        idx = np.random.randint(0, len(meter_df))
        meter_df.at[idx, 'usage'] = -abs(np.random.normal(15, 10))
    for _ in range(20):
        idx = np.random.randint(0, len(meter_df))
        meter_df.at[idx, 'usage'] = abs(np.random.normal(800, 250))
    for _ in range(40):
        idx = np.random.randint(0, len(meter_df))
        meter_df.at[idx, 'usage'] = meter_df.at[idx, 'usage']
        if idx + 1 < len(meter_df):
            meter_df.iloc[idx:idx + 2] = meter_df.iloc[idx:idx + 2].copy()
            meter_df.iloc[idx, 0] = meter_df.iloc[idx, 0]

    exact_duplicate_indices = np.random.choice(len(meter_df), size=40, replace=False)
    duplicate_rows = meter_df.iloc[exact_duplicate_indices].copy()
    duplicate_rows['reading_id'] = duplicate_rows['reading_id'] + '-DUP'
    meter_df = pd.concat([meter_df, duplicate_rows], ignore_index=True)

    meter_df['meter_status'] = meter_df['meter_status'].replace({
        'Estimated': 'Estimated',
        'Normal': 'Normal',
    })
    meter_df['meter_status'] = meter_df['meter_status'].fillna('Normal')

    for cid in connection_df['connection_id'].sample(18, random_state=SEED):
        leak_date = pd.Timestamp(np.random.choice(all_dates))
        repair_date = leak_date + pd.Timedelta(days=np.random.randint(2, 18))
        leak_status = np.random.choice([1, 0], p=[0.7, 0.3])
        if leak_status == 1:
            maintenance_rows.append({
                'maintenance_id': f'M-{len(maintenance_rows)+1:04d}',
                'connection_id': cid,
                'leak_report': 1,
                'report_date': leak_date.strftime('%Y-%m-%d'),
                'repair_date': repair_date.strftime('%Y-%m-%d'),
            })
        else:
            maintenance_rows.append({
                'maintenance_id': f'M-{len(maintenance_rows)+1:04d}',
                'connection_id': cid,
                'leak_report': 0,
                'report_date': leak_date.strftime('%Y-%m-%d'),
                'repair_date': repair_date.strftime('%Y-%m-%d'),
            })

    meter_df.to_csv(RAW_DIR / 'meter.csv', index=False)
    connection_df.to_csv(RAW_DIR / 'connections.csv', index=False)
    pd.DataFrame(billing_rows).to_csv(RAW_DIR / 'billing.csv', index=False)
    weather_df.to_csv(RAW_DIR / 'weather.csv', index=False)
    pd.DataFrame(maintenance_rows).to_csv(RAW_DIR / 'maintenance.csv', index=False)

    data_dictionary = pd.DataFrame([
        ['meter.csv', 'reading_id', 'string', 'Unique daily reading identifier'],
        ['meter.csv', 'date', 'datetime', 'Date of the meter reading'],
        ['meter.csv', 'connection_id', 'string', 'Foreign key to connections.csv'],
        ['meter.csv', 'usage', 'float', 'Daily water usage in liters'],
        ['meter.csv', 'meter_status', 'string', 'Reading status such as Normal or Estimated'],
        ['connections.csv', 'connection_id', 'string', 'Unique connection identifier'],
        ['connections.csv', 'connection_type', 'string', 'Residential or Commercial classification'],
        ['connections.csv', 'locality', 'string', 'Service locality'],
        ['connections.csv', 'household_size_band', 'string', 'Household size band for residential customers'],
        ['connections.csv', 'connection_start_date', 'datetime', 'Service start date'],
        ['billing.csv', 'billing_id', 'string', 'Unique billing identifier'],
        ['billing.csv', 'connection_id', 'string', 'Foreign key to connection'],
        ['billing.csv', 'billing_cycle', 'string', 'Monthly billing period'],
        ['billing.csv', 'charge', 'float', 'Monthly charge in local currency'],
        ['weather.csv', 'date', 'datetime', 'Weather observation date'],
        ['weather.csv', 'locality', 'string', 'Weather locality'],
        ['weather.csv', 'temperature', 'float', 'Daily average temperature in Celsius'],
        ['weather.csv', 'rain', 'float', 'Daily rainfall amount in mm'],
        ['maintenance.csv', 'maintenance_id', 'string', 'Unique maintenance record identifier'],
        ['maintenance.csv', 'connection_id', 'string', 'Connection associated with a maintenance event'],
        ['maintenance.csv', 'leak_report', 'integer', '1 if a leak was reported, 0 otherwise'],
        ['maintenance.csv', 'report_date', 'datetime', 'Date the leak was reported'],
        ['maintenance.csv', 'repair_date', 'datetime', 'Date the repair was completed'],
    ], columns=['file', 'column', 'data_type', 'meaning'])
    data_dictionary.to_csv(RAW_DIR / 'data_dictionary.csv', index=False)


if __name__ == '__main__':
    generate_synthetic_data()
    print(f'Generated synthetic data in {RAW_DIR}')
