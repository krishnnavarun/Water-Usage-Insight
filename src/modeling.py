from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import f1_score, precision_score, recall_score

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / 'data' / 'processed'
MODEL_DIR = ROOT / 'models'
OUTPUT_DIR = ROOT / 'outputs'

FEATURE_COLUMNS = [
    'usage', 'temperature', 'rain', 'usage_lag_1', 'rolling_mean_7',
    'recent_change', 'usage_deviation', 'usage_zscore',
    'connection_type_encoding', 'weekend', 'days_since_repair', 'is_repair_period',
]


def train_anomaly_model(contamination: float = 0.02) -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(PROCESSED_DIR / 'feature_ready.csv', parse_dates=['date'])
    X = df[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan).fillna(0)
    model = IsolationForest(n_estimators=250, contamination=contamination, random_state=42, n_jobs=-1)
    model.fit(X)
    df['anomaly_score'] = -model.score_samples(X)
    df['model_anomaly'] = (model.predict(X) == -1).astype(int)
    labels = df['anomaly_label'].astype(int)
    predictions = df['model_anomaly']
    metrics = {
        'rows_scored': int(len(df)),
        'feature_columns': FEATURE_COLUMNS,
        'contamination': contamination,
        'predicted_anomalies': int(predictions.sum()),
        'predicted_anomaly_rate': float(predictions.mean()),
        'known_anomalies': int(labels.sum()),
        'precision': float(precision_score(labels, predictions, zero_division=0)),
        'recall': float(recall_score(labels, predictions, zero_division=0)),
        'f1': float(f1_score(labels, predictions, zero_division=0)),
    }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({'model': model, 'features': FEATURE_COLUMNS}, MODEL_DIR / 'isolation_forest.joblib')
    df.to_csv(OUTPUT_DIR / 'scored_usage.csv', index=False)
    with open(OUTPUT_DIR / 'model_metrics.json', 'w', encoding='utf-8') as handle:
        json.dump(metrics, handle, indent=2)
    return df, metrics


if __name__ == '__main__':
    _, result = train_anomaly_model()
    print(json.dumps(result, indent=2))
