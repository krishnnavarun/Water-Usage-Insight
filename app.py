from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
SCORED_PATH = ROOT / 'outputs' / 'scored_usage.csv'

st.set_page_config(page_title='Water Usage Insight', page_icon='W', layout='wide')
st.title('Water Usage Insight')
st.caption('Operational view of water consumption, anomalies, weather, and maintenance signals.')

if not SCORED_PATH.exists():
    st.error('No scored dataset found. Run `python run_pipeline.py` first.')
    st.stop()

df = pd.read_csv(SCORED_PATH, parse_dates=['date'])
localities = ['All'] + sorted(df['locality'].dropna().unique().tolist())
selected_locality = st.sidebar.selectbox('Locality', localities)
selected_type = st.sidebar.multiselect('Connection type', sorted(df['connection_type'].dropna().unique()), default=sorted(df['connection_type'].dropna().unique()))
filtered = df if selected_locality == 'All' else df[df['locality'] == selected_locality]
filtered = filtered[filtered['connection_type'].isin(selected_type)]

cards = st.columns(4)
cards[0].metric('Average usage', f"{filtered['usage'].mean():,.1f}")
cards[1].metric('Readings', f"{len(filtered):,}")
cards[2].metric('Model anomalies', f"{filtered['model_anomaly'].sum():,}")
cards[3].metric('Leak-period readings', f"{filtered['leak_report'].sum():,}")

left, right = st.columns(2)
with left:
    st.subheader('Average usage over time')
    st.line_chart(filtered.groupby('date')['usage'].mean())
with right:
    st.subheader('Usage by locality')
    st.bar_chart(filtered.groupby('locality')['usage'].mean().sort_values(ascending=False))

st.subheader('Priority investigation queue')
queue = filtered[filtered['model_anomaly'] == 1].sort_values('anomaly_score', ascending=False)
st.dataframe(queue[['date', 'connection_id', 'locality', 'connection_type', 'usage', 'anomaly_score', 'leak_report']].head(100), use_container_width=True, hide_index=True)
