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
class RedFlag:
    """Represents a potential red flag found in a filing."""
    category: str
    description: str
    severity: str
    context: str 