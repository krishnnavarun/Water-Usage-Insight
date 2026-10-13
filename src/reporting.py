from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from openpyxl.styles import Font, PatternFill
from pptx import Presentation
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / 'outputs'


def build_insights(df: pd.DataFrame) -> dict:
    df = df.copy()
    locality = df.groupby('locality')['usage'].mean().sort_values(ascending=False)
    connection_type = df.groupby('connection_type')['usage'].mean().sort_values(ascending=False)
    repair = df[df['leak_report'] == 1].groupby('connection_id')['usage'].agg(['mean', 'count'])
    anomaly_rows = df[df['model_anomaly'] == 1].sort_values('anomaly_score', ascending=False)
    return {
        'row_count': int(len(df)),
        'date_start': str(df['date'].min().date()),
        'date_end': str(df['date'].max().date()),
        'mean_usage': float(df['usage'].mean()),
        'median_usage': float(df['usage'].median()),
        'top_locality': str(locality.index[0]),
        'top_locality_mean_usage': float(locality.iloc[0]),
        'connection_type_means': {str(k): float(v) for k, v in connection_type.items()},
        'reported_leak_readings': int(df['leak_report'].sum()),
        'model_anomalies': int(df['model_anomaly'].sum()),
        'top_anomaly_connection': str(anomaly_rows.iloc[0]['connection_id']) if not anomaly_rows.empty else None,
        'repair_connection_count': int(len(repair)),
    }


def create_charts(df: pd.DataFrame) -> None:
    sns.set_theme(style='whitegrid')
    chart_dir = OUTPUT_DIR / 'charts'
    chart_dir.mkdir(parents=True, exist_ok=True)
    daily = df.groupby('date', as_index=False)['usage'].mean()
    plt.figure(figsize=(10, 4))
    plt.plot(daily['date'], daily['usage'], color='#167c80', linewidth=1)
    plt.title('Average Daily Water Usage')
    plt.xlabel('Date')
    plt.ylabel('Usage')
    plt.tight_layout()
    plt.savefig(chart_dir / 'daily_usage.png', dpi=150)
    plt.close()

    plt.figure(figsize=(8, 4))
    locality = df.groupby('locality', as_index=False)['usage'].mean().sort_values('usage', ascending=False)
    sns.barplot(data=locality, x='usage', y='locality', color='#35a7a0')
    plt.title('Average Usage by Locality')
    plt.xlabel('Average usage')
    plt.ylabel('')
    plt.tight_layout()
    plt.savefig(chart_dir / 'locality_usage.png', dpi=150)
    plt.close()

    plt.figure(figsize=(8, 4))
    sns.scatterplot(data=df.sample(min(5000, len(df)), random_state=42), x='temperature', y='usage', hue='connection_type', alpha=0.45)
    plt.title('Temperature and Water Usage')
    plt.tight_layout()
    plt.savefig(chart_dir / 'weather_usage.png', dpi=150)
    plt.close()


def create_excel(df: pd.DataFrame, insights: dict, metrics: dict) -> Path:
    path = OUTPUT_DIR / 'water_usage_insight.xlsx'
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        pd.DataFrame([insights]).to_excel(writer, sheet_name='Executive Summary', index=False)
        pd.DataFrame([metrics]).drop(columns=['feature_columns']).to_excel(writer, sheet_name='Model Metrics', index=False)
        df.sort_values('anomaly_score', ascending=False).head(250).to_excel(writer, sheet_name='Top Anomalies', index=False)
        df.groupby(['locality', 'connection_type'], as_index=False).agg(
            average_usage=('usage', 'mean'),
            readings=('usage', 'size'),
            anomalies=('model_anomaly', 'sum'),
        ).to_excel(writer, sheet_name='Segment Summary', index=False)
    workbook = __import__('openpyxl').load_workbook(path)
    for sheet in workbook.worksheets:
        sheet.freeze_panes = 'A2'
        for cell in sheet[1]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='167C80')
    workbook.save(path)
    return path


def _add_title(slide, title: str, subtitle: str = '') -> None:
    box = slide.shapes.add_textbox(Inches(0.6), Inches(0.35), Inches(12), Inches(0.8))
    frame = box.text_frame
    frame.text = title
    frame.paragraphs[0].font.size = Pt(26)
    frame.paragraphs[0].font.bold = True
    if subtitle:
        sub = slide.shapes.add_textbox(Inches(0.62), Inches(1.1), Inches(11), Inches(0.45))
        sub.text_frame.text = subtitle
        sub.text_frame.paragraphs[0].font.size = Pt(13)


def create_powerpoint(insights: dict, metrics: dict) -> Path:
    path = OUTPUT_DIR / 'water_usage_insight.pptx'
    presentation = Presentation()
    presentation.slide_width = Inches(13.333)
    presentation.slide_height = Inches(7.5)
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    _add_title(slide, 'Water Usage Insight', 'Usage monitoring, anomaly detection, and conservation priorities')
    body = slide.shapes.add_textbox(Inches(0.8), Inches(2), Inches(11.5), Inches(3.8))
    body.text_frame.text = f"Analysis period: {insights['date_start']} to {insights['date_end']}\nRows analyzed: {insights['row_count']:,}\nAverage daily reading: {insights['mean_usage']:.1f}\nModel-flagged anomalies: {insights['model_anomalies']:,}"
    body.text_frame.paragraphs[0].font.size = Pt(22)

    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    _add_title(slide, 'What the data says')
    body = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.5), Inches(4.8))
    body.text_frame.text = f"Highest average locality: {insights['top_locality']} ({insights['top_locality_mean_usage']:.1f})\nReported leak-period readings: {insights['reported_leak_readings']:,}\nTop anomaly connection: {insights['top_anomaly_connection'] or 'None'}\nResidential average: {insights['connection_type_means'].get('Residential', 0):.1f}\nCommercial average: {insights['connection_type_means'].get('Commercial', 0):.1f}"
    body.text_frame.paragraphs[0].font.size = Pt(20)

    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    _add_title(slide, 'Model validation and action')
    body = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.5), Inches(4.8))
    body.text_frame.text = f"Isolation Forest precision: {metrics['precision']:.3f}\nRecall against generated investigation labels: {metrics['recall']:.3f}\nF1 score: {metrics['f1']:.3f}\n\nPrioritize field checks for repeated anomalies, validate meters with extreme readings, and monitor usage after maintenance events."
    body.text_frame.paragraphs[0].font.size = Pt(20)
    presentation.save(path)
    return path


def generate_reports(df: pd.DataFrame, metrics: dict) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    insights = build_insights(df)
    create_charts(df)
    excel_path = create_excel(df, insights, metrics)
    pptx_path = create_powerpoint(insights, metrics)
    with open(OUTPUT_DIR / 'insights.json', 'w', encoding='utf-8') as handle:
        json.dump(insights, handle, indent=2)
    return {'insights': insights, 'excel': str(excel_path), 'powerpoint': str(pptx_path)}
