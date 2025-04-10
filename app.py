"""
Streamlit app for SEC filing analysis.
"""

import streamlit as st
from sec_analyzer.downloader import download_filing
from sec_analyzer.semantic_processor import process_html, analyze_company_focus
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="SEC Filing Analyzer", layout="wide")

st.title("SEC Filing Analyzer")

# Input fields
col1, col2 = st.columns(2)
with col1:
    ticker = st.text_input("Enter Ticker Symbol", "AAPL")
with col2:
    form_type = st.text_input("Enter Form Type", "10-K")

if st.button("Get Filing"):
    with st.spinner("Downloading and analyzing filing..."):
        try:
            # Download and process the filing
            html_content = download_filing(ticker, form_type)
            result = process_html(html_content, form_type)
            
            # Display financial metrics
            st.header("Financial Metrics")
            metrics_cols = st.columns(3)
            for i, metric in enumerate(result['metrics']):
                with metrics_cols[i % 3]:
                    st.metric(
                        label=metric.name,
                        value=f"${metric.value:,.2f}",
                        delta=None
                    )
            
            # Display financial ratios
            st.header("Financial Ratios")
            ratio_cols = st.columns(3)
            for i, ratio in enumerate(result['ratios']):
                with ratio_cols[i % 3]:
                    st.metric(
                        label=ratio.name,
                        value=f"{ratio.value:.2%}" if ratio.unit == '%' else f"{ratio.value:.2f}x",
                        delta=None
                    )
            
            # Display red flags
            st.header("Red Flags")
            for flag in result['red_flags']:
                with st.expander(f"{flag.category} - {flag.description} ({flag.severity})"):
                    st.write(flag.context)
            
            # Display company focus analysis
            st.header("Company Focus Analysis")
            
            # Create focus area scores dataframe
            focus_data = []
            for area, data in result['focus_analysis']['focus_areas'].items():
                focus_data.append({
                    'Area': area,
                    'Score': data['score'],
                    'Relative Score': data['relative_score']
                })
            
            focus_df = pd.DataFrame(focus_data)
            
            # Plot focus areas
            fig = px.bar(focus_df, 
                        x='Area', 
                        y='Relative Score',
                        title='Company Focus Areas',
                        labels={'Relative Score': 'Relative Importance'})
            st.plotly_chart(fig)
            
            # Display top terms
            st.subheader("Top Terms")
            terms_df = pd.DataFrame(result['focus_analysis']['top_terms'], 
                                  columns=['Term', 'Frequency'])
            st.dataframe(terms_df)
            
            # Display document structure
            st.header("Document Structure")
            for element in result['elements']:
                if element.type == 'heading':
                    st.subheader(element.content.get_text())
                elif element.type == 'text':
                    st.write(element.content.get_text())
            
        except Exception as e:
            st.error(f"Error processing filing: {str(e)}") 