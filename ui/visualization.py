# ui/visualization.py
"""Visualization utilities for Streamlit app"""
import pandas as pd
import plotly.express as px
from typing import Optional

def create_company_chart(df: pd.DataFrame, top_n: int = 10):
    """Create bar chart of top companies"""
    if not isinstance(df, pd.DataFrame) or "company_name" not in df.columns:
        return None
    
    vc = df["company_name"].value_counts().reset_index()
    vc.columns = ["Company", "Count"]
    top_companies = vc.head(top_n)
    
    fig = px.bar(
        top_companies, x="Company", y="Count", color="Company",
        color_discrete_sequence=px.colors.sequential.Plasma_r, 
        text="Count", template="plotly_dark",
    )
    
    fig.update_layout(
        showlegend=False, 
        xaxis_title="", 
        yaxis_title="Jobs", 
        bargap=0.2,
        margin=dict(t=30, l=20, r=20, b=30), 
        height=340,
    )
    fig.update_traces(textfont_size=14)
    
    return fig

def create_timeline_chart(df: pd.DataFrame):
    """Create timeline chart of posting dates"""
    if not isinstance(df, pd.DataFrame) or "job_posting_date" not in df.columns:
        return None
    
    ts = pd.to_datetime(df["job_posting_date"], errors="coerce").dropna()
    if ts.empty:
        return None
    
    daily = ts.value_counts().sort_index()
    df_daily = daily.reset_index()
    df_daily.columns = ["Date", "Count"]
    
    fig = px.line(
        df_daily, x="Date", y="Count", 
        markers=True, template="plotly_dark", 
        line_shape="spline",
    )
    
    fig.update_layout(
        xaxis=dict(showgrid=True, tickformat="%b %d"),
        yaxis=dict(title="Jobs"),
        margin=dict(t=30, l=20, r=20, b=30), 
        height=300,
    )
    
    return fig