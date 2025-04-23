"""
Streamlit app for SEC filing analysis.
"""

import streamlit as st
from sec_analyzer.downloader import download_filing
from sec_analyzer.semantic_processor import process_html, analyze_company_focus, display_document_structure
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
            
            # Display risks analysis
            st.header("Risk Analysis")
            if result['risks']:
                # Display summary analysis
                st.subheader("Summary Analysis")
                for category_summary in result['risk_summary']:
                    with st.expander(f"{category_summary['category']} - {category_summary['high_severity_count']} High Severity, {category_summary['medium_severity_count']} Medium Severity Issues"):
                        for risk in category_summary['risks']:
                            st.write(f"**{risk.severity} Severity**: {risk.context}")
                
                # Display detailed analysis
                st.subheader("Detailed Analysis")
                for risk in result['risks']:
                    with st.expander(f"{risk.category} - {risk.description} ({risk.severity})"):
                        st.write(risk.context)
            else:
                st.warning("No risks were detected. This could be because:")
                st.write("- The relevant sections were not found in the document")
                st.write("- The sections were found but no risks were identified")
                st.write("- There was an error processing the document")
            
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
            display_document_structure(result['document_structure'])
            
        except Exception as e:
            st.error(f"Error processing filing: {str(e)}")

def display_document_structure(structure):
    """Display the document structure using nested expanders."""
    for section in structure:
        # Display Section
        with st.expander(f"📑 {section['title']} ({section['type']})", expanded=False):
            # Display section content if any
            if section['content']:
                for content in section['content']:
                    if content['type'] == 'table':
                        st.write(content['content'])
                    else:
                        st.write(content['content'])
            
            # Display Subsections
            for subsection in section['subsections']:
                with st.expander(f"📄 {subsection['title']}", expanded=False):
                    for content in subsection['content']:
                        if content['type'] == 'table':
                            st.write(content['content'])
                        else:
                            st.write(content['content']) 