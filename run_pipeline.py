from __future__ import annotations

import json

from src.feature_engineering import save_engineered_features
from src.generate_data import generate_synthetic_data
from src.modeling import train_anomaly_model
from src.preprocessing import create_processed_dataset
from src.reporting import generate_reports


def main() -> None:
    generate_synthetic_data()
    create_processed_dataset()
    save_engineered_features()
    scored, metrics = train_anomaly_model()
    reports = generate_reports(scored, metrics)
    print(json.dumps({'metrics': metrics, 'reports': reports}, indent=2))


if __name__ == '__main__':
    main()
