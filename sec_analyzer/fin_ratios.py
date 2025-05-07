from financetoolkit import Toolkit
import pandas as pd


def safe_get(df, key, alternative_keys=None):
    """Safely get a value from DataFrame with fallback keys."""
    try:
        return df.loc[key]
    except KeyError:
        if alternative_keys:
            for alt_key in alternative_keys:
                try:
                    return df.loc[alt_key]
                except KeyError:
                    continue
        return pd.Series([None] * len(df.columns), index=df.columns)

def get_financial_metrics(ticker: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Get all financial metrics for a given ticker.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Tuple of three DataFrames: (balance_sheet, income_statement, cash_flow)
    """
    # Initialize the Toolkit
    companies = Toolkit([ticker], api_key=API_KEY, start_date='2023-12-31')

    # Get financial statements
    balance_sheet = companies.get_balance_sheet_statement()
    income_statement = companies.get_income_statement()
    cash_flow = companies.get_cash_flow_statement()

    # Return raw numeric data
    return balance_sheet, income_statement, cash_flow

def get_financial_ratios(ticker: str) -> pd.DataFrame:
    """
    Get financial ratios for a given ticker.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        DataFrame containing all financial ratios
    """
    # Initialize the Toolkit
    companies = Toolkit([ticker], api_key=API_KEY, start_date='2023-12-31')

    # Collect all ratios
    efficiency = companies.ratios.collect_efficiency_ratios()
    liquidity = companies.ratios.collect_liquidity_ratios().drop('Working Capital', errors='ignore')
    profitability = companies.ratios.collect_profitability_ratios().drop(['Interest Coverage Ratio', 'Income Before Tax Ratio'], errors='ignore')
    solvency = companies.ratios.collect_solvency_ratios()
    valuation = companies.ratios.collect_valuation_ratios().drop(['Price to Earnings Growth Ratio', 'Interest Debt per Share', 'CAPEX per Share'], errors='ignore')

    # Combine all ratios into a single DataFrame
    all_ratios = pd.concat([efficiency, liquidity, profitability, solvency, valuation])
    return all_ratios

def analyze_balance_sheet_yoy(ticker: str) -> pd.DataFrame:
    """
    Analyze year-over-year changes in balance sheet metrics.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        DataFrame containing YoY changes for balance sheet metrics
    """
    # Get balance sheet data
    balance_sheet, _, _ = get_financial_metrics(ticker)
    
    # Calculate year-over-year changes
    yoy_changes = pd.DataFrame()
    
    # Get all available years
    years = sorted(balance_sheet.columns, reverse=True)
    
    # Calculate changes for each metric
    for metric in balance_sheet.index:
        values = balance_sheet.loc[metric]
        changes = []
        
        # Calculate percentage change for each year compared to previous year
        for i in range(len(years)-1):
            current_year = years[i]
            previous_year = years[i+1]
            
            current_value = values[current_year]
            previous_value = values[previous_year]
            
            if previous_value != 0 and not pd.isna(current_value) and not pd.isna(previous_value):
                change = ((current_value - previous_value) / abs(previous_value)) * 100
                changes.append(change)
            else:
                changes.append(None)
        
        # Add the changes to the DataFrame
        yoy_changes[metric] = changes
    
    # Set the index to be the year pairs (e.g., "2023 vs 2022")
    year_pairs = [f"{years[i]} vs {years[i+1]}" for i in range(len(years)-1)]
    yoy_changes.index = year_pairs
    
    # Format the changes as percentages
    yoy_changes = yoy_changes.applymap(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
    
    return yoy_changes

def format_yoy_changes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Format year-over-year changes DataFrame for display.
    
    Args:
        df: DataFrame containing YoY changes
        
    Returns:
        Formatted DataFrame with color coding and improved readability
    """
    # Create a copy of the DataFrame
    formatted_df = df.copy()
    
    # Reset index to make year pairs a column
    formatted_df = formatted_df.reset_index()
    formatted_df = formatted_df.rename(columns={'index': 'Year Comparison'})
    
    # Reorder columns to put Year Comparison first
    cols = ['Year Comparison'] + [col for col in formatted_df.columns if col != 'Year Comparison']
    formatted_df = formatted_df[cols]
    
    return formatted_df

def analyze_income_statement_yoy(ticker: str) -> pd.DataFrame:
    """
    Analyze year-over-year changes in income statement metrics.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        DataFrame containing YoY changes for income statement metrics
    """
    # Get income statement data
    _, income_statement, _ = get_financial_metrics(ticker)
    
    # Calculate year-over-year changes
    yoy_changes = pd.DataFrame()
    
    # Get all available years
    years = sorted(income_statement.columns, reverse=True)
    
    # Calculate changes for each metric
    for metric in income_statement.index:
        values = income_statement.loc[metric]
        changes = []
        
        # Calculate percentage change for each year compared to previous year
        for i in range(len(years)-1):
            current_year = years[i]
            previous_year = years[i+1]
            
            current_value = values[current_year]
            previous_value = values[previous_year]
            
            if previous_value != 0 and not pd.isna(current_value) and not pd.isna(previous_value):
                change = ((current_value - previous_value) / abs(previous_value)) * 100
                changes.append(change)
            else:
                changes.append(None)
        
        # Add the changes to the DataFrame
        yoy_changes[metric] = changes
    
    # Set the index to be the year pairs (e.g., "2023 vs 2022")
    year_pairs = [f"{years[i]} vs {years[i+1]}" for i in range(len(years)-1)]
    yoy_changes.index = year_pairs
    
    # Format the changes as percentages
    yoy_changes = yoy_changes.applymap(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
    
    return yoy_changes

def analyze_cash_flow_yoy(ticker: str) -> pd.DataFrame:
    """
    Analyze year-over-year changes in cash flow statement metrics.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        DataFrame containing YoY changes for cash flow metrics
    """
    # Get cash flow data
    _, _, cash_flow = get_financial_metrics(ticker)
    
    # Calculate year-over-year changes
    yoy_changes = pd.DataFrame()
    
    # Get all available years
    years = sorted(cash_flow.columns, reverse=True)
    
    # Calculate changes for each metric
    for metric in cash_flow.index:
        values = cash_flow.loc[metric]
        changes = []
        
        # Calculate percentage change for each year compared to previous year
        for i in range(len(years)-1):
            current_year = years[i]
            previous_year = years[i+1]
            
            current_value = values[current_year]
            previous_value = values[previous_year]
            
            if previous_value != 0 and not pd.isna(current_value) and not pd.isna(previous_value):
                change = ((current_value - previous_value) / abs(previous_value)) * 100
                changes.append(change)
            else:
                changes.append(None)
        
        # Add the changes to the DataFrame
        yoy_changes[metric] = changes
    
    # Set the index to be the year pairs (e.g., "2023 vs 2022")
    year_pairs = [f"{years[i]} vs {years[i+1]}" for i in range(len(years)-1)]
    yoy_changes.index = year_pairs
    
    # Format the changes as percentages
    yoy_changes = yoy_changes.applymap(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
    
    return yoy_changes

"""
Liquidity Ratios: Remove Working Capital
Profitability Ratios: Remove interest coverage ratio, income before tax ratio, 
Valuation Ratios: Remove Price-to-Earnings growth ratio, Interest Debt per share ratio, CAPEX per share

"""
