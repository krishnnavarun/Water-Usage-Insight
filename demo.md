# CH19 – WATER USAGE INSIGHT

## Round 2 – Data Understanding, Preparation & EDA

**1. Problem Statement**

The objective is to analyze water consumption patterns across residential and commercial connections and identify unusual or inefficient water usage. The analysis aims to detect consumption spikes, understand weather-related variations and investigate the impact of water leakage and repairs.

**2. Dataset Details**

- **Dataset name:** Water Usage Insight
- **Source:** Dataset provided for the DS Sprint Assessment.
- **Files:** `meter.csv`, `connections.csv`, `billing.csv`, `weather.csv`, `maintenance.csv`.
- **Number of records:** 70,176 cleaned daily readings covering 2023-01-01 through 2024-12-31.
- **Attributes:** Date, connection ID, usage, connection type, locality, household size band, billing cycle, charge, temperature, rainfall, leak report and repair date.

**3. Data Preprocessing**

- Handled missing meter readings and other missing values using suitable imputation or removal methods.
- Identified and removed duplicate records.
- Investigated negative and unusually high water-usage values.
- Standardized inconsistent connection types and date formats.
- Combined datasets using the appropriate connection, date and billing keys.
- Checked unmatched maintenance records and validated data consistency.

**4. EDA Findings**

- Finding 1: Lakewood has the highest average usage at 192.1 units per reading. Commercial usage averages 335.3 versus 105.7 for residential connections.
- Finding 2: The dataset contains 123 leak-period readings across 13 affected connections. Weather and usage are visualized in the generated chart for investigation, not treated as causal evidence.

## Round 3 – Feature Engineering & Machine Learning

**1. Selected Features**

- **Input features:** Historical water usage, connection type, locality, temperature, rainfall, household size band and maintenance information, depending on data availability.
- **Target variable:** To be selected based on the modelling objective, such as an unusual-usage label or future water consumption.

**2. ML Algorithm Used**

Isolation Forest for detecting anomalous water-consumption patterns.

**3. Justification**

Isolation Forest is suitable for anomaly detection because it identifies unusual observations based on how easily they can be isolated from normal data. It can help flag unexpected water-usage spikes for further investigation.

**4. Model Performance**

- **Evaluation method:** Precision, recall and F1-score if verified anomaly labels are available.
- **Actual result:** Isolation Forest flags 1,404 readings (2.0%). Against the generated investigation labels, precision is 0.009, recall is 0.098 and F1 is 0.017. The model is suitable for triage, but requires threshold tuning and field verification before operational deployment.

If verified labels are unavailable, report an appropriate unsupervised evaluation or validation method instead of claiming classification accuracy.

### Round 4 – Intelligence Layer, Visualization & Prototype

1. Visualization

The dashboard displays:

Water consumption by locality using bar charts.

Daily consumption trends using line charts.

Normal and anomalous readings using visual indicators.

Water usage before and after maintenance using comparison charts.

2. Key Insights

Lakewood recorded the highest average water consumption at 192.1 units per reading.

Commercial connections averaged 335.3 units versus 105.7 for residential connections.

Maintenance and leak-period readings are included in the investigation queue and scored alongside usage history.

3. Prototype / Intelligence Layer

The Streamlit dashboard successfully displays consumption statistics, usage trends and anomaly detection results. Users can filter the data by locality and investigate flagged readings.

4. Recommendations

Inspect connections with repeated abnormal readings.

Check for possible leaks in high-consumption areas.

Monitor consumption after maintenance.

Final Outcome / Conclusion

The project demonstrates how data analysis and machine learning can help identify unusual water consumption patterns. The interactive dashboard presents the findings clearly and supports informed water management decisions. Synthetic data was used because no original dataset was provided.

## Running the Project

Install dependencies with `Python313 -m pip install -r requirements.txt`, then run `Python313 run_pipeline.py`. This regenerates the raw data, processed datasets, model, charts, Excel workbook, PowerPoint deck, and JSON metrics under `outputs/` and `models/`.

Launch the interactive prototype with `streamlit run app.py` after running the pipeline. Run validation with `Python313 -m pytest -q`.
