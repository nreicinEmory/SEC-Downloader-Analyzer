"""
Module for processing SEC filings into sections and extracting key information.
"""

import re
import logging
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any
from .parsing.parsers import SEC10KParser, SEC10QParser
from .types import FinancialMetric, RedFlag, SemanticElement

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_html(html_content: str, form_type: str = '10-K') -> Dict[str, Any]:
    """Process HTML content and extract key information."""
    logger.info("Starting HTML processing")
    
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Create semantic elements
    elements = []
    
    # Process tables
    for table in soup.find_all('table'):
        elements.append(SemanticElement(
            type='table',
            content=table
        ))
    
    # Process headings
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        elements.append(SemanticElement(
            type='heading',
            content=heading
        ))
    
    # Process text paragraphs
    for p in soup.find_all('p'):
        elements.append(SemanticElement(
            type='text',
            content=p
        ))
    
    logger.info(f"Parsed {len(elements)} semantic elements")
    
    try:
        # Extract financial data
        financial_data = extract_financial_data(elements)
        
        # Find red flags
        red_flags = find_red_flags(elements)
        
        # Analyze company focus
        focus_analysis = analyze_company_focus(elements)
        
        result = {
            'elements': elements,
            'metrics': financial_data['metrics'],
            'ratios': financial_data['ratios'],
            'red_flags': red_flags,
            'focus_analysis': focus_analysis
        }
        
        logger.info("HTML processing completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error processing HTML: {str(e)}", exc_info=True)
        raise

def extract_section_content(element) -> str:
    """Extract content from a section element."""
    content = [element.text]
    for child in element.children:
        content.append(child.text)
    return '\n'.join(content)

def is_financial_statement(table: 'SemanticElement') -> bool:
    """Check if a table is likely a financial statement."""
    if not table.content:
        return False
        
    # Get the text from the table and its surrounding context
    table_text = table.content.get_text().lower()
    parent_text = table.parent.get_text().lower() if table.parent else ""
    
    # Combine table and parent text for better context
    context = f"{parent_text} {table_text}"
    
    # Check for financial statement indicators
    indicators = [
        'balance sheet', 'income statement', 'statement of operations',
        'statement of cash flows', 'statement of financial position',
        'consolidated statements', 'financial statements',
        'revenue', 'net income', 'total assets', 'total liabilities',
        'cash and equivalents', 'operating income'
    ]
    
    return any(indicator in context for indicator in indicators)

def get_table_scale(table: 'SemanticElement') -> int:
    """Determine the scale of numbers in a table based on surrounding text."""
    if not table.content:
        return 1
        
    # Get text from table and surrounding context
    table_text = table.content.get_text().lower()
    parent_text = table.parent.get_text().lower() if table.parent else ""
    context = f"{parent_text} {table_text}"
    
    # Look for scale indicators in the context
    if 'millions' in context or '(in millions)' in context:
        return 1_000_000
    elif 'billions' in context or '(in billions)' in context:
        return 1_000_000_000
    elif 'thousands' in context or '(in thousands)' in context:
        return 1_000
    return 1

def extract_financial_data(elements: List['SemanticElement']) -> Dict[str, Any]:
    """Extract financial data from semantic elements."""
    result = {
        'metrics': [],
        'ratios': [],
        'periods': set()
    }
    
    # Track the most recent value for each metric
    latest_metrics = {}
    
    for element in elements:
        if element.type == 'table' and is_financial_statement(element):
            logger.info("Found financial statement table")
            
            # Get the scale for this table
            scale = get_table_scale(element)
            logger.info(f"Detected scale: {scale}")
            
            # Find header row and data rows
            header_row = None
            data_rows = []
            
            for row in element.content.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                if not cells:
                    continue
                    
                # Check if this is a header row
                if any('$' in cell.get_text() for cell in cells):
                    header_row = cells
                else:
                    data_rows.append(cells)
            
            if not header_row or not data_rows:
                continue
                
            # Process data rows
            for row in data_rows:
                if len(row) < 2:
                    continue
                    
                label = row[0].get_text().strip().lower()
                value_cells = row[1:]
                
                # Extract values for each period
                for i, cell in enumerate(value_cells):
                    value_text = cell.get_text().strip()
                    if not value_text:
                        continue
                        
                    try:
                        parsed_value = parse_amount(value_text)
                        if parsed_value is None:
                            logger.debug(f"Could not parse value from text: {value_text}")
                            continue
                            
                        value = parsed_value * scale
                        
                        # Create metric key based on label
                        metric_key = None
                        if 'revenue' in label or 'sales' in label:
                            metric_key = 'Revenue'
                        elif 'gross profit' in label:
                            metric_key = 'Gross Profit'
                        elif 'operating income' in label or 'operating profit' in label:
                            metric_key = 'Operating Income'
                        elif 'net income' in label:
                            metric_key = 'Net Income'
                        elif 'total assets' in label:
                            metric_key = 'Total Assets'
                        elif 'total liabilities' in label:
                            metric_key = 'Total Liabilities'
                        elif 'cash' in label and 'equivalents' in label:
                            metric_key = 'Cash and Equivalents'
                        elif 'inventory' in label:
                            metric_key = 'Inventory'
                        elif 'accounts receivable' in label:
                            metric_key = 'Accounts Receivable'
                        elif 'accounts payable' in label:
                            metric_key = 'Accounts Payable'
                        elif 'research' in label and 'development' in label:
                            metric_key = 'R&D Expenses'
                        elif 'depreciation' in label:
                            metric_key = 'Depreciation'
                        elif 'amortization' in label:
                            metric_key = 'Amortization'
                        elif 'capital expenditures' in label:
                            metric_key = 'Capital Expenditures'
                        elif 'dividends' in label:
                            metric_key = 'Dividends'
                        elif 'stockholders' in label and 'equity' in label:
                            metric_key = 'Stockholders Equity'
                        elif 'long-term debt' in label:
                            metric_key = 'Long-term Debt'
                        elif 'short-term debt' in label:
                            metric_key = 'Short-term Debt'
                            
                        if metric_key:
                            # Update the latest value for this metric
                            latest_metrics[metric_key] = value
                            
                    except ValueError as e:
                        logger.warning(f"Error parsing value '{value_text}': {e}")
                        continue
    
    # Add the latest values to the result
    for metric_name, value in latest_metrics.items():
        result['metrics'].append(FinancialMetric(metric_name, value, 'USD'))
    
    # Calculate financial ratios using the latest values
    metrics_dict = {m.name: m.value for m in result['metrics']}
    
    # Profitability Ratios
    if 'Revenue' in metrics_dict and 'Net Income' in metrics_dict and metrics_dict['Revenue'] != 0:
        result['ratios'].append(FinancialMetric('Net Profit Margin', 
            (metrics_dict['Net Income'] / metrics_dict['Revenue']) * 100, '%'))
    
    if 'Revenue' in metrics_dict and 'Gross Profit' in metrics_dict and metrics_dict['Revenue'] != 0:
        result['ratios'].append(FinancialMetric('Gross Margin', 
            (metrics_dict['Gross Profit'] / metrics_dict['Revenue']) * 100, '%'))
    
    if 'Operating Income' in metrics_dict and 'Revenue' in metrics_dict and metrics_dict['Revenue'] != 0:
        result['ratios'].append(FinancialMetric('Operating Margin', 
            (metrics_dict['Operating Income'] / metrics_dict['Revenue']) * 100, '%'))
    
    # Liquidity Ratios
    if 'Total Assets' in metrics_dict and 'Total Liabilities' in metrics_dict and metrics_dict['Total Assets'] != 0:
        result['ratios'].append(FinancialMetric('Debt to Assets', 
            (metrics_dict['Total Liabilities'] / metrics_dict['Total Assets']) * 100, '%'))
    
    if 'Cash and Equivalents' in metrics_dict and 'Total Liabilities' in metrics_dict and metrics_dict['Total Liabilities'] != 0:
        result['ratios'].append(FinancialMetric('Cash to Debt', 
            (metrics_dict['Cash and Equivalents'] / metrics_dict['Total Liabilities']) * 100, '%'))
    
    # Efficiency Ratios
    if 'Revenue' in metrics_dict and 'Accounts Receivable' in metrics_dict and metrics_dict['Accounts Receivable'] != 0:
        result['ratios'].append(FinancialMetric('Receivables Turnover', 
            (metrics_dict['Revenue'] / metrics_dict['Accounts Receivable']), 'x'))
    
    if 'Revenue' in metrics_dict and 'Inventory' in metrics_dict and metrics_dict['Inventory'] != 0:
        result['ratios'].append(FinancialMetric('Inventory Turnover', 
            (metrics_dict['Revenue'] / metrics_dict['Inventory']), 'x'))
    
    # Growth Metrics
    if 'R&D Expenses' in metrics_dict and 'Revenue' in metrics_dict and metrics_dict['Revenue'] != 0:
        result['ratios'].append(FinancialMetric('R&D to Revenue', 
            (metrics_dict['R&D Expenses'] / metrics_dict['Revenue']) * 100, '%'))
    
    if 'Capital Expenditures' in metrics_dict and 'Revenue' in metrics_dict and metrics_dict['Revenue'] != 0:
        result['ratios'].append(FinancialMetric('Capex to Revenue', 
            (metrics_dict['Capital Expenditures'] / metrics_dict['Revenue']) * 100, '%'))
    
    return result

def parse_amount(text: str) -> Optional[float]:
    """Parse a financial amount from text, handling various formats and scales."""
    if not text:
        logger.debug("Empty text provided to parse_amount")
        return None
        
    # Remove any non-numeric characters except decimal point, minus sign, and scale indicators
    cleaned = text.strip()
    logger.debug(f"Attempting to parse amount from text: {cleaned}")
    
    # Handle negative numbers in parentheses
    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = '-' + cleaned[1:-1]
        logger.debug(f"Converted parentheses to negative: {cleaned}")
    
    # Extract scale from the text
    scale = 1
    if 'million' in cleaned.lower() or 'm' in cleaned.lower():
        scale = 1_000_000
        cleaned = cleaned.lower().replace('million', '').replace('m', '')
        logger.debug(f"Detected millions scale: {cleaned}")
    elif 'billion' in cleaned.lower() or 'b' in cleaned.lower():
        scale = 1_000_000_000
        cleaned = cleaned.lower().replace('billion', '').replace('b', '')
        logger.debug(f"Detected billions scale: {cleaned}")
    elif 'thousand' in cleaned.lower() or 'k' in cleaned.lower():
        scale = 1_000
        cleaned = cleaned.lower().replace('thousand', '').replace('k', '')
        logger.debug(f"Detected thousands scale: {cleaned}")
    
    # Remove any remaining non-numeric characters
    cleaned = ''.join(c for c in cleaned if c.isdigit() or c in '.-')
    logger.debug(f"Cleaned text: {cleaned}")
    
    if not cleaned:
        logger.debug("No numeric characters found after cleaning")
        return None
        
    try:
        # Handle scientific notation
        if 'e' in cleaned.lower() or 'e-' in cleaned.lower():
            value = float(cleaned)
            logger.debug(f"Parsed scientific notation: {value}")
        else:
            # Handle regular numbers
            value = float(cleaned.replace(',', ''))
            logger.debug(f"Parsed regular number: {value}")
            
        # Apply scale
        result = value * scale
        logger.debug(f"Final value after scale: {result}")
        return result
        
    except ValueError as e:
        logger.warning(f"Could not parse amount from text: {text}. Error: {str(e)}")
        return None

def find_red_flags(elements: List['SemanticElement']) -> List['RedFlag']:
    """Find potential red flags in the filing."""
    red_flags = []
    current_section = "Unknown Section"
    
    # Define red flag categories and their associated terms
    red_flag_categories = {
        'Financial Health': {
            'terms': [
                'going concern', 'substantial doubt', 'material weakness',
                'liquidity issues', 'debt covenant', 'default', 'bankruptcy',
                'significant loss', 'operating loss', 'net loss'
            ],
            'severity': 'High'
        },
        'Financial Reporting': {
            'terms': [
                'restatement', 'material error', 'accounting error',
                'internal control', 'audit issues', 'disagreement with auditor',
                'material weakness', 'significant deficiency'
            ],
            'severity': 'High'
        },
        'Management and Governance': {
            'terms': [
                'ceo change', 'cfo change', 'management change',
                'related party transaction', 'conflict of interest',
                'executive compensation', 'board changes'
            ],
            'severity': 'Medium'
        },
        'Operational': {
            'terms': [
                'supply chain disruption', 'cyber attack', 'data breach',
                'operational disruption', 'production issues',
                'quality control issues', 'recall'
            ],
            'severity': 'Medium'
        },
        'Legal and Regulatory': {
            'terms': [
                'regulatory investigation', 'enforcement action',
                'legal proceedings', 'lawsuit', 'class action',
                'regulatory compliance', 'fines', 'penalties'
            ],
            'severity': 'High'
        },
        'Market and Competition': {
            'terms': [
                'market share decline', 'pricing pressure',
                'competitive pressure', 'market disruption',
                'customer loss', 'key customer'
            ],
            'severity': 'Medium'
        },
        'Innovation and Growth': {
            'terms': [
                'product delay', 'patent expiration',
                'intellectual property', 'research setback',
                'development delay', 'technology risk'
            ],
            'severity': 'Medium'
        }
    }
    
    for element in elements:
        if not element.content:
            continue
            
        # Update current section if this is a heading
        if element.type == 'heading':
            current_section = element.content.get_text().strip()
            continue
            
        # Get the text content
        text = element.content.get_text().lower()
        
        # Check each category
        for category, info in red_flag_categories.items():
            for term in info['terms']:
                if term in text:
                    # Get a snippet of the context
                    start_idx = max(0, text.find(term) - 50)
                    end_idx = min(len(text), text.find(term) + len(term) + 50)
                    context = text[start_idx:end_idx].strip()
                    
                    # Clean up the section name
                    section_name = current_section.replace('\n', ' ').strip()
                    if len(section_name) > 50:
                        section_name = section_name[:47] + "..."
                    
                    red_flags.append(RedFlag(
                        category=category,
                        description=f"Found '{term}' in {section_name}",
                        severity=info['severity'],
                        context=context
                    ))
    
    return red_flags

def analyze_company_focus(elements: List['SemanticElement']) -> Dict[str, Any]:
    """Analyze company focus areas using NLP techniques."""
    from collections import Counter
    import nltk
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    
    # Download required NLTK resources
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords')
    
    # Define focus areas and their keywords
    focus_areas = {
        'Innovation': ['research', 'development', 'innovation', 'patent', 'technology', 'r&d'],
        'Growth': ['growth', 'expansion', 'acquisition', 'market share', 'new market'],
        'Efficiency': ['efficiency', 'cost reduction', 'optimization', 'productivity'],
        'Sustainability': ['sustainability', 'environmental', 'green', 'carbon', 'renewable'],
        'Customer Focus': ['customer', 'user', 'experience', 'satisfaction', 'service'],
        'Financial': ['profit', 'margin', 'revenue', 'earnings', 'dividend', 'shareholder'],
        'Risk': ['risk', 'uncertainty', 'challenge', 'threat', 'competition'],
        'Regulatory': ['regulation', 'compliance', 'legal', 'policy', 'government']
    }
    
    # Combine all text from elements
    all_text = ' '.join(element.content.get_text() for element in elements if element.content)
    
    # Tokenize and clean text
    tokens = word_tokenize(all_text.lower())
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token.isalnum() and token not in stop_words]
    
    # Count word frequencies
    word_counts = Counter(tokens)
    
    # Analyze focus areas
    focus_analysis = {}
    for area, keywords in focus_areas.items():
        score = sum(word_counts[word] for word in keywords)
        focus_analysis[area] = {
            'score': score,
            'relative_score': score / len(tokens) if tokens else 0,
            'key_terms': [word for word in keywords if word_counts[word] > 0]
        }
    
    # Get top 10 most frequent terms
    top_terms = word_counts.most_common(10)
    
    return {
        'focus_areas': focus_analysis,
        'top_terms': top_terms,
        'total_words': len(tokens)
    } 