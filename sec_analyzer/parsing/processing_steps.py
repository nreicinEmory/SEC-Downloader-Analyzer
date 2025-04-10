"""
Processing steps for SEC filing parsing.
"""

from typing import List, Set
from .abstract_parser import AbstractProcessingStep, SemanticElement

class TableClassifier(AbstractProcessingStep):
    """Classifies table elements."""
    
    def process(self, elements: List[SemanticElement]) -> List[SemanticElement]:
        for element in elements:
            if element.tag.name == 'table':
                element.type = 'table'
        return elements

class SectionClassifier(AbstractProcessingStep):
    """Classifies section headings and organizes content."""
    
    def __init__(self):
        self.section_markers = {
            'financial_statements': [
                'consolidated financial statements',
                'financial statements',
                'balance sheet',
                'income statement',
                'statement of operations',
                'statement of cash flows'
            ],
            'mdna': [
                'management\'s discussion',
                'results of operations',
                'liquidity and capital resources'
            ],
            'risk_factors': [
                'risk factors',
                'risk factors summary'
            ]
        }
    
    def process(self, elements: List[SemanticElement]) -> List[SemanticElement]:
        current_section = None
        result = []
        
        for element in elements:
            if element.tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                text = element.text.lower()
                for section_type, markers in self.section_markers.items():
                    if any(marker in text for marker in markers):
                        current_section = SemanticElement(element.tag)
                        current_section.type = section_type
                        result.append(current_section)
                        break
            elif current_section:
                current_section.add_child(element)
            else:
                result.append(element)
        
        return result

class TextClassifier(AbstractProcessingStep):
    """Classifies text elements based on their content."""
    
    def process(self, elements: List[SemanticElement]) -> List[SemanticElement]:
        for element in elements:
            if element.type == 'not_yet_classified' and element.tag.name in ['p', 'div']:
                text = element.text.lower()
                if any(keyword in text for keyword in ['note', 'footnote']):
                    element.type = 'footnote'
                elif any(keyword in text for keyword in ['table', 'exhibit']):
                    element.type = 'reference'
                else:
                    element.type = 'text'
        return elements

class FinancialDataExtractor(AbstractProcessingStep):
    """Extracts financial data from tables and text."""
    
    def process(self, elements: List[SemanticElement]) -> List[SemanticElement]:
        for element in elements:
            if element.type == 'table':
                self._extract_from_table(element)
            elif element.type == 'text':
                self._extract_from_text(element)
        return elements
    
    def _extract_from_table(self, element: SemanticElement):
        """Extract financial data from a table element."""
        # Implementation for table extraction
        pass
    
    def _extract_from_text(self, element: SemanticElement):
        """Extract financial data from a text element."""
        # Implementation for text extraction
        pass 