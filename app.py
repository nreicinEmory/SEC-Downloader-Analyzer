"""
Streamlit app for SEC filing analysis.
"""

import streamlit as st
from sec_analyzer.downloader import download_filing
from sec_analyzer.semantic_processor import process_html, analyze_company_focus, display_document_structure
from sec_analyzer.fin_ratios import (
    get_financial_ratios, 
    get_financial_metrics,
    analyze_balance_sheet_yoy,
    analyze_income_statement_yoy,
    analyze_cash_flow_yoy,
    format_yoy_changes
)
import plotly.express as px
import pandas as pd

def format_currency_value(x):
    """Format currency values in billions or millions with commas and parentheses for negatives."""
    if isinstance(x, (int, float)):
        if x == 0:
            return None  # Return None for zero values to be filtered out later
        abs_x = abs(x)
        if abs_x >= 1_000_000_000:  # Billions
            formatted = f"{abs_x/1_000_000_000:,.2f}B"
        elif abs_x >= 1_000_000:  # Millions
            formatted = f"{abs_x/1_000_000:,.2f}M"
        else:
            formatted = f"{abs_x:,.2f}"
        
        # Use parentheses for negatives instead of minus sign
        return f"(${formatted})" if x < 0 else f"${formatted}"
    return x

def format_ratio_value(x):
    """Format ratio values as percentages or decimals without currency symbols."""
    if isinstance(x, (int, float)):
        if x == 0:
            return None  # Return None for zero values to be filtered out later
        # If the ratio is already a percentage (between 0 and 1), format as percentage
        if abs(x) <= 1:
            return f"{x:.2%}"
        # Otherwise format as decimal with 2 places
        return f"{x:,.2f}"
    return x

def format_financial_data(df, is_ratios=False):
    """Format financial data, removing zeros and formatting appropriately."""
    # Convert to numeric if not already
    df = df.apply(pd.to_numeric, errors='coerce')
    
    # Remove rows where all values are zero or NaN
    df = df.loc[~(df == 0).all(axis=1) & ~df.isna().all(axis=1)]
    
    # For ratios, only keep the most recent year (remove 2023)
    if is_ratios and '2023' in df.columns:
        df = df.drop('2023', axis=1)
    
    # Format each row based on its content
    formatted_df = df.copy()
    for index, row in df.iterrows():
        if is_ratios:
            # For ratios, format as percentage or decimal
            formatted_df.loc[index] = row.apply(format_ratio_value)
        else:
            # For financial metrics, format as currency
            formatted_df.loc[index] = row.apply(format_currency_value)
    
    # Remove any columns that are all None (after formatting)
    formatted_df = formatted_df.dropna(how='all', axis=1)
    
    # Reset index to make metrics a column
    formatted_df = formatted_df.reset_index()
    # Rename the index column to 'Metric'
    formatted_df = formatted_df.rename(columns={'index': 'Metric'})
    
    return formatted_df

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
            # Display financial metrics in three sections
            st.header("Financial Metrics")
            
            # Get the three financial statement DataFrames
            balance_sheet_df, income_statement_df, cash_flow_df = get_financial_metrics(ticker)
            
            # Display Balance Sheet in an expander
            with st.expander("📊 Balance Sheet", expanded=False):
                balance_sheet_formatted = format_financial_data(balance_sheet_df)
                st.dataframe(balance_sheet_formatted, use_container_width=True, hide_index=True)
                
                # Add Year-over-Year Analysis
                st.subheader("Year-over-Year Changes")
                yoy_changes = analyze_balance_sheet_yoy(ticker)
                yoy_formatted = format_yoy_changes(yoy_changes)
                
                # Apply color coding to the DataFrame
                def color_negative_red(val):
                    if isinstance(val, str) and val != "N/A" and val != "Year Comparison":
                        try:
                            value = float(val.strip('%'))
                            color = 'red' if value < 0 else 'green'
                            return f'color: {color}'
                        except ValueError:
                            return ''
                    return ''
                
                # Apply styling only to numeric columns
                styled_df = yoy_formatted.style.applymap(color_negative_red, subset=yoy_formatted.columns[1:])
                
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True
                )
            
            # Display Income Statement in an expander
            with st.expander("📈 Income Statement", expanded=False):
                income_statement_formatted = format_financial_data(income_statement_df)
                st.dataframe(income_statement_formatted, use_container_width=True, hide_index=True)
                
                # Add Year-over-Year Analysis
                st.subheader("Year-over-Year Changes")
                yoy_changes = analyze_income_statement_yoy(ticker)
                yoy_formatted = format_yoy_changes(yoy_changes)
                styled_df = yoy_formatted.style.applymap(color_negative_red, subset=yoy_formatted.columns[1:])
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            # Display Cash Flow in an expander
            with st.expander("💰 Cash Flow", expanded=False):
                cash_flow_formatted = format_financial_data(cash_flow_df)
                st.dataframe(cash_flow_formatted, use_container_width=True, hide_index=True)
                
                # Add Year-over-Year Analysis
                st.subheader("Year-over-Year Changes")
                yoy_changes = analyze_cash_flow_yoy(ticker)
                yoy_formatted = format_yoy_changes(yoy_changes)
                styled_df = yoy_formatted.style.applymap(color_negative_red, subset=yoy_formatted.columns[1:])
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            # Display financial ratios
            st.header("Financial Ratios")
            ratios_df = get_financial_ratios(ticker)
            ratios_formatted = format_financial_data(ratios_df, is_ratios=True)
            st.dataframe(ratios_formatted, use_container_width=True, hide_index=True)
            
            # Download and process the filing
            html_content = download_filing(ticker, form_type)
            result = process_html(html_content, form_type)
            
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