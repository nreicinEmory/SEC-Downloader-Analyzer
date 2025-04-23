from financetoolkit import Toolkit
import pandas as pd

API_KEY = "dGNRQtg75qUy2p1ONrPp47JT4xNd0FtW"

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

"""
Liquidity Ratios: Remove Working Capital
Profitability Ratios: Remove interest coverage ratio, income before tax ratio, 
Valuation Ratios: Remove Price-to-Earnings growth ratio, Interest Debt per share ratio, CAPEX per share

"""