"""
Abstract base classes for SEC filing parsing.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from bs4 import BeautifulSoup, Tag

class AbstractProcessingStep(ABC):
    """Base class for processing steps in the parsing pipeline."""
    
    @abstractmethod
    def process(self, elements: List['SemanticElement']) -> List['SemanticElement']:
        """Process a list of semantic elements and return the processed elements."""
        pass

class SemanticElement:
    """Base class for semantic elements in SEC filings."""
    
    def __init__(self, tag: Tag):
        self.tag = tag
        self.text = tag.get_text().strip()
        self.type = "not_yet_classified"
        self.children: List[SemanticElement] = []
    
    def add_child(self, child: 'SemanticElement'):
        """Add a child element to this element."""
        self.children.append(child)

class AbstractParser(ABC):
    """
    Base class for SEC filing parsers.
    Implements a pipeline pattern for processing HTML content.
    """
    
    def __init__(self):
        self.steps = self.get_processing_steps()
    
    @abstractmethod
    def get_processing_steps(self) -> List[AbstractProcessingStep]:
        """Get the list of processing steps for this parser."""
        pass
    
    def parse(self, html: str) -> List[SemanticElement]:
        """Parse HTML content into semantic elements."""
        soup = BeautifulSoup(html, 'html.parser')
        root_tags = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'p', 'table'])
        
        # Convert HTML tags to initial semantic elements
        elements = [SemanticElement(tag) for tag in root_tags]
        
        # Process elements through each step
        for step in self.steps:
            elements = step.process(elements)
        
        return elements 