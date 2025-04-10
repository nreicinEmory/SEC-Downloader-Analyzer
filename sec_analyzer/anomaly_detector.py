"""
Module for detecting anomalies and red flags in SEC filings.
"""

from typing import Dict, List, Any
import numpy as np
from scipy import stats
import pandas as pd
from sec_analyzer.types import FinancialFlag
from sec_analyzer.types import SemanticElement
import re

class AnomalyDetector:
    def __init__(self):
        self.risk_patterns = {
            'financial_risk': r'(?:debt|loss|decline|decrease|risk|uncertainty|volatility)',
            'operational_risk': r'(?:challenge|difficulty|issue|problem|failure|disruption)',
            'regulatory_risk': r'(?:regulation|compliance|investigation|enforcement|violation)',
            'market_risk': r'(?:competition|market share|pricing pressure|demand|supply)'
        }
        
        self.red_flag_patterns = {
            'auditor_opinion': r'(qualified|unqualified)\s*opinion',
            'management_changes': r'(resignation|appointment|change)\s*of\s*(CEO|CFO|director)',
            'related_party': r'related\s*party\s*transaction',
            'material_weakness': r'material\s*weakness\s*in\s*internal\s*control',
            'accounting_change': r'change\s*in\s*accounting\s*principle',
            'restatement': r'(?:restatement|revision|correction).*?(?:financial|results|earnings)',
            'impairment': r'(?:impairment|write-down|write-off).*?(\$?\d+(?:,\d{3})*(?:\.\d{2})?)',
            'legal_issue': r'(?:litigation|legal|lawsuit).*?(\$?\d+(?:,\d{3})*(?:\.\d{2})?)'
        }

    def detect_anomalies(self, element: SemanticElement) -> List[FinancialFlag]:
        """
        Detect anomalies and red flags in a semantic element.
        
        Args:
            element: SemanticElement to analyze
            
        Returns:
            List of detected FinancialFlags
        """
        flags = []
        text = element.content.lower()
        section_name = element.element_type

        # Check for red flags
        for category, pattern in self.red_flag_patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                severity = self._determine_severity(category, match.group(0))
                flag = FinancialFlag(
                    category=category,
                    description=match.group(0),
                    severity=severity,
                    context=text[max(0, match.start()-100):min(len(text), match.end()+100)]
                )
                flags.append(flag)

        # Check for risk factors
        for category, pattern in self.risk_patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                flag = FinancialFlag(
                    category=f'risk_{category}',
                    description=match.group(0),
                    severity='medium',
                    context=text[max(0, match.start()-100):min(len(text), match.end()+100)]
                )
                flags.append(flag)

        return flags

    def _determine_severity(self, category: str, match: str) -> str:
        """Determine the severity of a red flag based on its category and content."""
        if category in ['auditor_opinion', 'material_weakness', 'restatement', 'impairment', 'legal_issue']:
            return 'high'
        elif category in ['management_changes', 'related_party', 'accounting_change']:
            return 'medium'
        return 'low'

    def analyze_metric_anomalies(self, metrics: Dict[str, float], historical_metrics: List[Dict[str, float]]) -> List[FinancialFlag]:
        """
        Analyze financial metrics for statistical anomalies.
        
        Args:
            metrics: Current period metrics
            historical_metrics: List of historical metrics
            
        Returns:
            List of detected FinancialFlags
        """
        flags = []
        
        if not historical_metrics:
            return flags
            
        df = pd.DataFrame(historical_metrics)
        
        for metric, value in metrics.items():
            if metric in df.columns:
                # Calculate z-score
                mean = df[metric].mean()
                std = df[metric].std()
                if std != 0:
                    z_score = (value - mean) / std
                    
                    # Flag significant deviations
                    if abs(z_score) > 2:
                        severity = 'high' if abs(z_score) > 3 else 'medium'
                        flag = FinancialFlag(
                            category='metric_anomaly',
                            description=f"Significant deviation in {metric} (z-score: {z_score:.2f})",
                            severity=severity,
                            context=f"Current value: {value:.2f}, Historical mean: {mean:.2f}, Std dev: {std:.2f}"
                        )
                        flags.append(flag)
        
        return flags