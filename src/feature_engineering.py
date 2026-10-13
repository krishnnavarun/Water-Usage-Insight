from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / 'data' / 'processed'


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values(['connection_id', 'date']).reset_index(drop=True)
    df['day_of_week'] = df['date'].dt.dayofweek
    df['month'] = df['date'].dt.month
    df['weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    df['usage_lag_1'] = df.groupby('connection_id')['usage'].shift(1)
    df['rolling_mean_7'] = df.groupby('connection_id')['usage'].transform(lambda s: s.rolling(window=7, min_periods=1).mean())
    df['recent_change'] = df['usage'] - df['usage_lag_1']
    df['usage_deviation'] = df['usage'] - df['rolling_mean_7']
    df['usage_zscore'] = (df['usage'] - df.groupby('connection_id')['usage'].transform('mean')) / df.groupby('connection_id')['usage'].transform('std').replace(0, 1)
    df['connection_type_encoding'] = df['connection_type'].map({'Residential': 0, 'Commercial': 1}).fillna(0)
    return df.sort_values(['date', 'connection_id']).reset_index(drop=True)


def save_engineered_features() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED_DIR / 'analysis_ready.csv')
    df['date'] = pd.to_datetime(df['date'])
    df = engineer_features(df)
    df.to_csv(PROCESSED_DIR / 'feature_ready.csv', index=False)
    return df


if __name__ == '__main__':
    save_engineered_features()
    print('Feature engineering complete')
