from pathlib import Path

import pandas as pd

from src.feature_engineering import engineer_features
from src.modeling import FEATURE_COLUMNS


def test_feature_lags_are_calculated_within_connection():
    source = pd.DataFrame({
        'connection_id': ['B', 'A', 'A', 'B'],
        'date': pd.to_datetime(['2024-01-02', '2024-01-02', '2024-01-01', '2024-01-01']),
        'usage': [20, 10, 5, 15],
        'connection_type': ['Commercial', 'Residential', 'Residential', 'Commercial'],
    })
    result = engineer_features(source)
    a_rows = result[result['connection_id'] == 'A'].sort_values('date')
    assert pd.isna(a_rows.iloc[0]['usage_lag_1'])
    assert a_rows.iloc[1]['usage_lag_1'] == 5


def test_model_feature_contract_is_present():
    assert 'usage_zscore' in FEATURE_COLUMNS
    assert 'is_repair_period' in FEATURE_COLUMNS


def test_expected_artifact_paths_are_project_relative():
    assert Path('data/processed').exists()
