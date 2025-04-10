"""
Specific parser implementations for SEC filings.
"""

from .abstract_parser import AbstractParser
from .processing_steps import (
    TableClassifier,
    SectionClassifier,
    TextClassifier,
    FinancialDataExtractor
)

class SEC10KParser(AbstractParser):
    """Parser for SEC 10-K annual reports."""
    
    def get_processing_steps(self):
        return [
            TableClassifier(),
            SectionClassifier(),
            TextClassifier(),
            FinancialDataExtractor()
        ]

class SEC10QParser(AbstractParser):
    """Parser for SEC 10-Q quarterly reports."""
    
    def get_processing_steps(self):
        return [
            TableClassifier(),
            SectionClassifier(),
            TextClassifier(),
            FinancialDataExtractor()
        ] 