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
            
            # Display legal red flags
            st.header("Legal Proceedings Analysis")
            if result['legal_red_flags']:
                # Display summary analysis
                st.subheader("Summary Analysis")
                for category_summary in result['legal_summary']:
                    with st.expander(f"{category_summary['category']} - {category_summary['high_severity_count']} High Severity, {category_summary['medium_severity_count']} Medium Severity Issues"):
                        for flag in category_summary['flags']:
                            st.write(f"**{flag.severity} Severity**: {flag.context}")
                
                # Display detailed analysis
                st.subheader("Detailed Analysis")
                for flag in result['legal_red_flags']:
                    with st.expander(f"{flag.category} - {flag.description} ({flag.severity})"):
                        st.write(flag.context)
            else:
                st.warning("No legal red flags were detected. This could be because:")
                st.write("- The Legal Proceedings section was not found in the document")
                st.write("- The section was found but no red flags were identified")
                st.write("- There was an error processing the document")
            
            # Display MD&A insights
            st.header("Management Discussion & Analysis")
            if result['mda_insights']:
                # Display summary analysis
                st.subheader("Summary Analysis")
                for category_summary in result['mda_summary']:
                    with st.expander(f"{category_summary['category']} - {category_summary['high_significance_count']} High Significance, {category_summary['medium_significance_count']} Medium Significance Points"):
                        for insight in category_summary['insights']:
                            st.write(f"**{insight.severity} Significance**: {insight.context}")
                
                # Display detailed analysis
                st.subheader("Detailed Analysis")
                for insight in result['mda_insights']:
                    with st.expander(f"{insight.category} - {insight.description} ({insight.severity})"):
                        st.write(insight.context)
            else:
                st.warning("No MD&A insights were detected. This could be because:")
                st.write("- The MD&A section was not found in the document")
                st.write("- The section was found but no significant insights were identified")
                st.write("- There was an error processing the document")
                
                # Debug information
                st.subheader("Debug Information")
                st.write("Number of elements processed:", len(result['elements']))
                st.write("MD&A insights found:", len(result['mda_insights']))
                st.write("Summary analysis items:", len(result['mda_summary']))
            
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