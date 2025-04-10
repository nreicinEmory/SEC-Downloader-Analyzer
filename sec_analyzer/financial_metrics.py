from dataclasses import dataclass
from typing import Optional, Dict, List
import pandas as pd

@dataclass
class RawFinancialData:
    """Class to store raw financial data extracted from 10-K."""
    revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None
    inventory: Optional[float] = None
    accounts_receivable: Optional[float] = None
    total_debt: Optional[float] = None
    interest_expense: Optional[float] = None
    depreciation_amortization: Optional[float] = None
    eps: Optional[float] = None
    market_price: Optional[float] = None

class FinancialMetricsCalculator:
    def __init__(self, raw_data: RawFinancialData):
        self.raw_data = raw_data

    def calculate_metrics(self) -> Dict[str, float]:
        """Calculate all financial metrics from raw data."""
        metrics = {}

        # Profitability Ratios
        if self.raw_data.revenue and self.raw_data.gross_profit:
            metrics['gross_profit_margin'] = (self.raw_data.gross_profit / self.raw_data.revenue) * 100

        if self.raw_data.revenue and self.raw_data.net_income:
            metrics['net_profit_margin'] = (self.raw_data.net_income / self.raw_data.revenue) * 100

        if self.raw_data.operating_income and self.raw_data.depreciation_amortization:
            metrics['ebitda'] = self.raw_data.operating_income + self.raw_data.depreciation_amortization

        # Return Ratios
        if self.raw_data.net_income and self.raw_data.total_equity:
            metrics['roe'] = (self.raw_data.net_income / self.raw_data.total_equity) * 100

        if self.raw_data.net_income and self.raw_data.total_assets:
            metrics['roa'] = (self.raw_data.net_income / self.raw_data.total_assets) * 100

        # Liquidity Ratios
        if self.raw_data.current_assets and self.raw_data.current_liabilities:
            metrics['current_ratio'] = self.raw_data.current_assets / self.raw_data.current_liabilities
            if self.raw_data.inventory:
                metrics['quick_ratio'] = (self.raw_data.current_assets - self.raw_data.inventory) / self.raw_data.current_liabilities
            metrics['working_capital'] = self.raw_data.current_assets - self.raw_data.current_liabilities

        # Leverage Ratios
        if self.raw_data.total_debt and self.raw_data.total_equity:
            metrics['debt_to_equity'] = self.raw_data.total_debt / self.raw_data.total_equity

        if self.raw_data.operating_income and self.raw_data.total_debt:
            metrics['dscr'] = self.raw_data.operating_income / self.raw_data.total_debt

        if self.raw_data.operating_income and self.raw_data.interest_expense:
            metrics['interest_coverage'] = self.raw_data.operating_income / self.raw_data.interest_expense

        # Efficiency Ratios
        if self.raw_data.revenue and self.raw_data.total_assets:
            metrics['asset_turnover'] = self.raw_data.revenue / self.raw_data.total_assets

        if self.raw_data.revenue and self.raw_data.inventory:
            metrics['inventory_turnover'] = self.raw_data.revenue / self.raw_data.inventory

        if self.raw_data.revenue and self.raw_data.accounts_receivable:
            metrics['receivables_turnover'] = self.raw_data.revenue / self.raw_data.accounts_receivable

        # Valuation Ratios
        if self.raw_data.market_price and self.raw_data.eps:
            metrics['pe_ratio'] = self.raw_data.market_price / self.raw_data.eps

        if self.raw_data.market_price and self.raw_data.total_equity:
            metrics['pb_ratio'] = self.raw_data.market_price / (self.raw_data.total_equity / 1000000)  # Assuming 1M shares

        return metrics

    def analyze_trends(self, historical_data: List[RawFinancialData]) -> Dict[str, Dict[str, float]]:
        """
        Analyze trends in financial metrics over time.
        
        Args:
            historical_data: List of RawFinancialData objects over time
            
        Returns:
            Dictionary containing trend analysis for each metric
        """
        if not historical_data:
            return {}
        
        # Convert historical data to DataFrame
        metrics_list = []
        for data in historical_data:
            metrics = self.calculate_metrics()
            metrics_list.append(metrics)
        
        df = pd.DataFrame(metrics_list)
        
        trends = {}
        for column in df.columns:
            if len(df[column]) >= 2:
                growth_rate = (df[column].iloc[-1] - df[column].iloc[0]) / df[column].iloc[0] * 100
                volatility = df[column].std() / df[column].mean() * 100
                trends[column] = {
                    'growth_rate': growth_rate,
                    'volatility': volatility
                }
        
        return trends 