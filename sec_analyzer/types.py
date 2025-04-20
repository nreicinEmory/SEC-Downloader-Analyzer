"""
Type definitions for the SEC analyzer.
"""

from dataclasses import dataclass
from typing import Optional, Any
from bs4 import BeautifulSoup

@dataclass
class SemanticElement:
    """Represents a semantic element in a document."""
    type: str
    content: Any
    text: str = ""
    parent: Optional['SemanticElement'] = None

@dataclass
class FinancialMetric:
    """Represents a financial metric extracted from a filing."""
    name: str
    value: float
    unit: str = "USD"
    period: Optional[str] = None

@dataclass
class RedFlag:
    """Represents a potential red flag found in a filing."""
    category: str
    description: str
    severity: str
    context: str 