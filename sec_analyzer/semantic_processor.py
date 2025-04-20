"""
Module for processing SEC filings into sections and extracting key information.
"""

import re
import logging
from bs4 import BeautifulSoup, Tag
from typing import Dict, List, Optional, Any, Tuple
from .parsing.parsers import SEC10KParser, SEC10QParser
from .types import FinancialMetric, RedFlag, SemanticElement
import streamlit as st

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_table_of_contents(soup: BeautifulSoup) -> List[Dict]:
    """Parse the table of contents and document content to create a hierarchical structure."""
    logger.info("Starting table of contents parsing")
    structure = []
    
    # Find the table of contents section
    toc_pattern = re.compile(r'table\s+of\s+contents', re.IGNORECASE)
    toc_section = None
    
    # Look for the table of contents in various possible locations
    for element in soup.find_all(['h1', 'h2', 'h3', 'div']):
        if toc_pattern.search(element.get_text()):
            toc_section = element
            break
    
    if not toc_section:
        logger.warning("Could not find table of contents section")
        return []
    
    # Find all items in the table of contents
    current_part = None
    current_items = []
    
    # Look for items in the table of contents
    for element in toc_section.find_all_next(['h1', 'h2', 'h3', 'div', 'p']):
        text = element.get_text().strip()
        
        # Check if this is a part header
        if re.match(r'^part\s+[iIvV]+$', text, re.IGNORECASE):
            # If we have a current part, add it to the structure
            if current_part and current_items:
                structure.append({
                    'title': current_part,
                    'items': current_items
                })
            current_part = text.upper()
            current_items = []
            continue
        
        # Check if this is an item
        item_match = re.match(r'^item\s+(\d+[A-Z]?)\s*\.?\s*(.*)$', text, re.IGNORECASE)
        if item_match:
            item_number = item_match.group(1)
            item_title = item_match.group(2).strip()
            
            # Handle reserved items
            if item_title.lower() == 'reserved':
                # If this is Item 6, it's the start of Part II
                if item_number == '6':
                    if current_part and current_items:
                        structure.append({
                            'title': current_part,
                            'items': current_items
                        })
                    current_part = 'PART II'
                    current_items = []
                continue
            
            # Skip items with no title or just numbers
            if not item_title or re.match(r'^\d+[A-Z]?\s*$', item_title):
                continue
            
            # Skip items that are just numbers separated by commas
            if re.match(r'^\d+[A-Z]?\s*,\s*\d+[A-Z]?\s*$', item_title):
                continue
            
            # Add the item with its full title
            current_items.append({
                'title': f"Item {item_number}. {item_title}",
                'item_number': item_number
            })
        
        # Stop if we hit the next major section
        if element.name in ['h1', 'h2'] and not re.match(r'^part\s+[iIvV]+$', text, re.IGNORECASE):
            break
    
    # Add the last part if it exists
    if current_part and current_items:
        structure.append({
            'title': current_part,
            'items': current_items
        })
    
    # Now find the content for each item
    for part in structure:
        for item in part['items']:
            section_content = find_section_content(soup, item['title'])
            item['content'] = section_content['content']
            item['subsections'] = section_content['subsections']
    
    logger.info(f"Completed table of contents parsing. Created structure with {len(structure)} parts")
    return structure

def process_html(html_content: str, form_type: str = '10-K') -> Dict[str, Any]:
    """Process HTML content and extract key information."""
    logger.info("Starting HTML processing")
    
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # First pass: Extract all semantic elements
    elements = []
    for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'table']):
        text = element.get_text().strip()
        if not text:
            continue
            
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            element_type = 'heading'
        elif element.name == 'table':
            element_type = 'table'
        else:
            element_type = 'text'
            
        elements.append(SemanticElement(
            type=element_type,
            content=element,
            text=text
        ))
    
    # Create document structure using the extracted elements
    document_structure = create_document_structure(elements)
    
    # Extract other information using the same elements
    financial_data = extract_financial_data(elements)
    legal_red_flags, legal_summary = find_legal_red_flags(elements)
    mda_insights, mda_summary = find_mda_insights(elements)
    focus_analysis = analyze_company_focus(elements)
    
    result = {
        'document_structure': document_structure,
        'metrics': financial_data['metrics'],
        'ratios': financial_data['ratios'],
        'legal_red_flags': legal_red_flags,
        'legal_summary': legal_summary,
        'mda_insights': mda_insights,
        'mda_summary': mda_summary,
        'focus_analysis': focus_analysis
    }
    
    return result

def create_document_structure(elements: List['SemanticElement']) -> List[Dict]:
    """Create a nested structure of the document using the processed elements."""
    structure = []
    current_part = None
    current_items = []
    
    for element in elements:
        # Skip navigation elements
        if any(marker in element.text.lower() for marker in ['table of contents', 'next page', 'previous page']):
            continue
        
        # Check if this is a part header
        if re.match(r'^part\s+[iIvV]+$', element.text, re.IGNORECASE):
            if current_part and current_items:
                structure.append({
                    'title': current_part,
                    'items': current_items
                })
            current_part = element.text.upper()
            current_items = []
            continue
        
        # Check if this is an item header
        item_match = re.match(r'^item\s+(\d+[A-Z]?)\s*\.?\s*(.*)$', element.text, re.IGNORECASE)
        if item_match:
            item_number = item_match.group(1)
            item_title = item_match.group(2).strip()
            
            # Handle reserved items
            if item_title.lower() == 'reserved':
                # If this is Item 6, it's the start of Part II
                if item_number == '6':
                    if current_part and current_items:
                        structure.append({
                            'title': current_part,
                            'items': current_items
                        })
                    current_part = 'PART II'
                    current_items = []
                continue
            
            if item_title:  # Only add if we have a title
                current_items.append({
                    'title': f"Item {item_number}. {item_title}",
                    'item_number': item_number,
                    'content': [],
                    'subsections': []
                })
        
        # Handle content for the current item
        elif current_items and element.type in ['text', 'table']:
            content = {
                'type': element.type,
                'content': element.text if element.type == 'text' else element.content
            }
            current_items[-1]['content'].append(content)
    
    # Add the last part if it exists
    if current_part and current_items:
        structure.append({
            'title': current_part,
            'items': current_items
        })
    
    return structure

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


def find_legal_red_flags(elements: List['SemanticElement']) -> Tuple[List[RedFlag], List[Dict]]:
    """Find legal red flags in the filing."""
    legal_red_flags = []
    current_section = None
    current_paragraph = []
    in_legal_section = False
    
    # Track processed contexts to avoid duplicates
    processed_contexts = []  # Changed from set to list to allow substring checking
    
    # Define legal red flag categories with more specific indicators
    legal_categories = {
        'Commercial Litigation': {
            'terms': [
                'lawsuit', 'litigation', 'legal proceeding', 'legal action',
                'class action', 'breach of contract', 'dispute', 'arbitration',
                'settlement', 'judgment', 'court order', 'trial', 'appeal',
                'complaint', 'defendant', 'plaintiff', 'damages', 'injunction',
                'motion to dismiss', 'summary judgment'
            ],
            'context_required': True
        },
        'Regulatory Investigations': {
            'terms': [
                'regulatory investigation', 'enforcement action', 'regulatory inquiry',
                'regulatory review', 'regulatory scrutiny', 'regulatory violation',
                'compliance issue', 'regulatory penalty', 'regulatory fine',
                'regulatory settlement', 'regulatory order', 'regulatory finding',
                'regulatory action', 'regulatory proceeding', 'regulatory matter'
            ],
            'context_required': True
        },
        'Antitrust Litigation': {
            'terms': [
                'antitrust', 'monopoly', 'market power', 'competition law',
                'anti-competitive', 'market dominance', 'unfair competition',
                'price fixing', 'market allocation', 'tying arrangement',
                'exclusive dealing', 'predatory pricing', 'merger challenge',
                'competition authority', 'competition commission'
            ],
            'context_required': True
        },
        'Intellectual Property': {
            'terms': [
                'patent infringement', 'trademark infringement', 'copyright infringement',
                'intellectual property', 'IP dispute', 'trade secret',
                'patent litigation', 'trademark litigation', 'copyright litigation',
                'IP litigation', 'patent claim', 'trademark claim', 'copyright claim',
                'patent dispute', 'trademark dispute', 'copyright dispute'
            ],
            'context_required': True
        },
        'Employment Litigation': {
            'terms': [
                'employment dispute', 'labor dispute', 'wage and hour',
                'discrimination', 'harassment', 'wrongful termination',
                'employment claim', 'labor claim', 'wage claim',
                'discrimination claim', 'harassment claim', 'wrongful termination claim',
                'employment lawsuit', 'labor lawsuit', 'wage lawsuit'
            ],
            'context_required': True
        }
    }
    
    # Section header patterns to ignore
    section_header_patterns = [
        r'^item\s*\d+\.?\s*legal\s+proceedings',
        r'^legal\s+proceedings',
        r'^other\s+legal\s+proceedings',
        r'^legal\s+matters',
        r'^litigation',
        r'^legal',
        r'^part\s+\d+',
        r'^item\s+\d+'
    ]
    
    # Legal section indicators - used to identify the Legal Proceedings section
    legal_section_indicators = [
        'lawsuit', 'litigation', 'legal proceeding', 'legal action',
        'court', 'judge', 'judgment', 'complaint', 'defendant', 'plaintiff',
        'arbitration', 'settlement', 'investigation', 'enforcement',
        'regulatory', 'antitrust', 'patent', 'trademark', 'copyright',
        'employment', 'labor', 'wage', 'discrimination', 'harassment'
    ]
    
    def is_section_header(text: str) -> bool:
        """Check if the text matches any section header patterns."""
        text = text.lower().strip()
        return any(re.match(pattern, text) for pattern in section_header_patterns)
    
    def normalize_text(text: str) -> str:
        """Normalize text for comparison by removing extra whitespace and punctuation."""
        # Convert to lowercase and remove extra whitespace
        text = ' '.join(text.lower().split())
        # Remove punctuation except periods (to preserve sentence boundaries)
        text = re.sub(r'[^\w\s\.]', '', text)
        return text
    
    def is_duplicate_or_contained(new_text: str, existing_texts: List[str]) -> bool:
        """Check if the new text is a duplicate or is contained within any existing text."""
        normalized_new = normalize_text(new_text)
        for existing in existing_texts:
            normalized_existing = normalize_text(existing)
            if normalized_new in normalized_existing or normalized_existing in normalized_new:
                return True
        return False
    
    for element in elements:
        if not element.content:
            continue
            
        # Get the text content
        try:
            text = element.text.strip()
            if not text:
                continue
                
            # Skip if this is a section header
            if is_section_header(text):
                if element.type == 'heading':
                    in_legal_section = True  # Mark that we're entering the legal section
                continue
                
            text_lower = text.lower()
            
        except Exception as e:
            logger.warning(f"Error getting text from element: {str(e)}")
            continue
            
        # Check if we're in the Legal Proceedings section
        if not in_legal_section:
            # Count legal indicators in the text
            legal_indicator_count = sum(1 for indicator in legal_section_indicators if indicator in text_lower)
            if legal_indicator_count >= 3:  # Require multiple indicators to avoid false positives
                in_legal_section = True
                logger.info(f"Entered Legal Proceedings section based on content: {text[:100]}...")
            else:
                continue
        
        # Add text to current paragraph if it's not a section header
        if not is_section_header(text):
            current_paragraph.append(text)
        
        # Check each category
        for category, config in legal_categories.items():
            found_terms = []
            for term in config['terms']:
                if term in text_lower:
                    found_terms.append(term)
            
            if found_terms:
                    # Get context (surrounding sentences)
                context = ' '.join(current_paragraph)
                
                # Skip if the context is too short (likely just a header)
                if len(context.split()) < 5:
                    continue
                    
                # Skip if we've already processed this context or if it's contained in another context
                if is_duplicate_or_contained(context, processed_contexts):
                        continue
                    
                processed_contexts.append(context)
                    
                # Determine severity based on context
                severity = 'Medium'
                if any(word in context.lower() for word in ['material', 'significant', 'substantial', 'major']):
                        severity = 'High'
                    
                    # Create the red flag
                legal_red_flags.append(RedFlag(
                        category=category,
                    description=f"Found legal issues related to: {', '.join(found_terms)}",
                        severity=severity,
                    context=context
                ))
                logger.info(f"Found legal red flag: {category} - {', '.join(found_terms)} - {severity}")
        
        # Reset paragraph if we hit a new major section
        if any(marker in text_lower for marker in ['item', 'part']):
            current_paragraph = []
            if not any(term in text_lower for term in ['legal', 'proceedings', 'litigation']):
                in_legal_section = False
    
    # Create summary analysis
    summary_analysis = []
    for category in legal_categories.keys():
        category_flags = [flag for flag in legal_red_flags if flag.category == category]
        if category_flags:
            summary_analysis.append({
                'category': category,
                'high_severity_count': sum(1 for flag in category_flags if flag.severity == 'High'),
                'medium_severity_count': sum(1 for flag in category_flags if flag.severity == 'Medium'),
                'flags': category_flags
            })
    
    # Sort red flags by severity (High first, then Medium)
    legal_red_flags.sort(key=lambda x: 0 if x.severity == 'High' else 1)
    
    return legal_red_flags, summary_analysis

def find_mda_insights(elements: List['SemanticElement']) -> Tuple[List[RedFlag], List[Dict]]:
    """Find insights in the Management Discussion & Analysis (MD&A) section."""
    mda_insights = []
    current_section = None
    current_paragraph = []
    in_mda_section = False
    
    # Track processed contexts to avoid duplicates
    processed_contexts = []
    
    # Define MD&A categories with specific indicators
    mda_categories = {
        'Financial Performance': {
            'terms': [
                'revenue growth', 'revenue decline', 'net income', 'profit margin',
                'operating margin', 'gross margin', 'earnings per share', 'cost of revenue',
                'operating expenses', 'operating income', 'net sales', 'income from operations',
                'profit', 'loss', 'cash flow', 'liquidity', 'capital resources'
            ],
            'context_required': True
        },
        'Market Conditions': {
            'terms': [
                'market conditions', 'competitive environment', 'industry trends',
                'market share', 'market position', 'competition', 'competitive pressure',
                'market demand', 'market growth', 'market opportunity', 'market risk',
                'economic conditions', 'macroeconomic', 'market dynamics'
            ],
            'context_required': True
        },
        'Operations': {
            'terms': [
                'supply chain', 'production', 'manufacturing', 'inventory',
                'distribution', 'operational efficiency', 'capacity utilization',
                'productivity', 'cost reduction', 'operating costs', 'infrastructure',
                'facilities', 'equipment', 'workforce', 'staffing'
            ],
            'context_required': True
        },
        'Strategy': {
            'terms': [
                'strategic initiatives', 'growth strategy', 'business strategy',
                'expansion plans', 'investment strategy', 'acquisition strategy',
                'product development', 'research and development', 'innovation',
                'market expansion', 'cost management', 'restructuring'
            ],
            'context_required': True
        },
        'Risk Factors': {
            'terms': [
                'risk factors', 'uncertainties', 'challenges', 'risks',
                'material changes', 'adverse effects', 'negative impact',
                'volatility', 'exposure', 'dependency', 'critical accounting',
                'significant estimates', 'contingencies'
            ],
            'context_required': True
        }
    }
    
    # Section header patterns to identify MD&A section
    section_header_patterns = [
        r'^item\s*[27]\.?\s*management.*discussion',
        r'^management.*discussion.*analysis',
        r'^md&a',
        r'^management.*analysis',
        r'^financial.*condition.*results',
        r'^results.*operations',
        r'^operating.*financial.*review',
        r'^part\s+\d+',
        r'^item\s+\d+'
    ]
    
    # MD&A section indicators
    mda_section_indicators = [
        'financial condition', 'results of operations', 'operating results',
        'financial performance', 'liquidity', 'capital resources',
        'critical accounting', 'market risk', 'forward-looking',
        'key performance', 'business outlook', 'future prospects'
    ]
    
    def is_section_header(text: str) -> bool:
        """Check if the text matches any section header patterns."""
        text = text.lower().strip()
        return any(re.match(pattern, text) for pattern in section_header_patterns)
    
    def normalize_text(text: str) -> str:
        """Normalize text for comparison by removing extra whitespace and punctuation."""
        text = ' '.join(text.lower().split())
        text = re.sub(r'[^\w\s\.]', '', text)
        return text
    
    def is_duplicate_or_contained(new_text: str, existing_texts: List[str]) -> bool:
        """Check if the new text is a duplicate or is contained within any existing text."""
        normalized_new = normalize_text(new_text)
        for existing in existing_texts:
            normalized_existing = normalize_text(existing)
            if normalized_new in normalized_existing or normalized_existing in normalized_new:
                return True
        return False
    
    for element in elements:
        if not element.content:
            continue
            
        try:
            text = element.text.strip()
            if not text:
                continue
                
            # Check for MD&A section headers
            if is_section_header(text):
                if element.type == 'heading':
                    if any(marker in text.lower() for marker in ['management', 'md&a', 'discussion']):
                        in_mda_section = True
                        logger.info(f"Entered MD&A section with header: {text}")
                    elif any(marker in text.lower() for marker in ['item', 'part']) and in_mda_section:
                        if not any(term in text.lower() for term in ['management', 'md&a', 'discussion']):
                            in_mda_section = False
                            logger.info("Exited MD&A section")
                continue
                
            text_lower = text.lower()
            
        except Exception as e:
            logger.warning(f"Error getting text from element: {str(e)}")
            continue
            
        # Check if we're in the MD&A section
        if not in_mda_section:
            # Count MD&A indicators in the text
            mda_indicator_count = sum(1 for indicator in mda_section_indicators if indicator in text_lower)
            if mda_indicator_count >= 2:  # Require multiple indicators to avoid false positives
                in_mda_section = True
                logger.info(f"Entered MD&A section based on content: {text[:100]}...")
            else:
                continue
        
        # Add text to current paragraph if it's not a section header
        if not is_section_header(text):
            current_paragraph.append(text)
        
        # Check each category
        for category, config in mda_categories.items():
            found_terms = []
            for term in config['terms']:
                if term in text_lower:
                    found_terms.append(term)
            
            if found_terms:
                # Get context (surrounding sentences)
                context = ' '.join(current_paragraph)
                
                # Skip if the context is too short (likely just a header)
                if len(context.split()) < 5:
                    continue
                    
                # Skip if we've already processed this context or if it's contained in another context
                if is_duplicate_or_contained(context, processed_contexts):
                    continue
                    
                processed_contexts.append(context)
                
                # Determine significance based on context
                significance = 'Medium'
                if any(word in context.lower() for word in [
                    'material', 'significant', 'substantial', 'major',
                    'critical', 'important', 'key', 'essential', 'fundamental'
                ]):
                    significance = 'High'
                
                # Create the insight
                mda_insights.append(RedFlag(
                    category=category,
                    description=f"Found {category.lower()} discussion related to: {', '.join(found_terms)}",
                    severity=significance,  # Using severity field for significance level
                    context=context
                ))
                logger.info(f"Found MD&A insight: {category} - {', '.join(found_terms)} - {significance}")
        
        # Reset paragraph if we hit a new major section
        if any(marker in text_lower for marker in ['item', 'part']):
            current_paragraph = []
            if not any(term in text_lower for term in ['management', 'md&a', 'discussion', 'analysis']):
                in_mda_section = False
    
    # Create summary analysis
    summary_analysis = []
    for category in mda_categories.keys():
        category_insights = [insight for insight in mda_insights if insight.category == category]
        if category_insights:
            summary_analysis.append({
                'category': category,
                'high_significance_count': sum(1 for insight in category_insights if insight.severity == 'High'),
                'medium_significance_count': sum(1 for insight in category_insights if insight.severity == 'Medium'),
                'insights': category_insights
            })
    
    # Sort insights by significance (High first, then Medium)
    mda_insights.sort(key=lambda x: 0 if x.severity == 'High' else 1)
    
    return mda_insights, summary_analysis

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
    try:
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        nltk.download('punkt_tab')

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
    all_text = ' '.join(element.text for element in elements if element.text)
    
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

def display_document_structure(structure):
    """Display the document structure using Streamlit's native components."""
    logger.info("Starting document structure display")
    
    if not structure:
        logger.warning("No document structure to display")
        st.warning("No document structure found")
        return
    
    # Group parts by their title to avoid duplicates
    grouped_parts = {}
    for part in structure:
        if part['title'] not in grouped_parts:
            grouped_parts[part['title']] = {
                'title': part['title'],
                'items': []
            }
        grouped_parts[part['title']]['items'].extend(part['items'])
    
    # Create tabs for each unique part
    part_tabs = st.tabs([part['title'] for part in grouped_parts.values()])
    
    for part_tab, part in zip(part_tabs, grouped_parts.values()):
        with part_tab:
            # Display items in a single column for better readability
            for item in part['items']:
                with st.expander(f"📄 {item['title']}", expanded=False):
                    # Display main content if any
                    if item['content']:
                        for content in item['content']:
                            if isinstance(content, dict) and content['type'] == 'text':
                                st.write(content['content'])
                                st.write("")  # Add spacing between paragraphs
                    
                    # Display subsections if any
                    if item['subsections']:
                        for subsection in item['subsections']:
                            with st.expander(f"📑 {subsection['title']}", expanded=False):
                                # Add indentation for subsection content
                                for content in subsection['content']:
                                    if isinstance(content, dict) and content['type'] == 'text':
                                        st.write("&nbsp;&nbsp;&nbsp;&nbsp;" + content['content'])
                                        st.write("")  # Add spacing between paragraphs
                    
                    if not item['content'] and not item['subsections']:
                        st.info("No content available for this section")

def find_section_content(soup: BeautifulSoup, section_title: str) -> Dict:
    """Find the content and subsections of a given section using regex patterns."""
    logger.info(f"Finding content for section: {section_title}")
    content = []
    subsections = []
    
    # Get the full HTML content
    html_content = str(soup)
    
    # Create regex pattern for the section
    # Handle both formats: "Item X. Title" and just "Title"
    if 'Item' in section_title:
        item_number = re.search(r'Item\s+(\d+[A-Z]?)', section_title)
        if item_number:
            # Pattern for "Item X. Title" format
            pattern = re.compile(
                rf'Item\s+{item_number.group(1)}\s*\.?\s*{re.escape(section_title.split(".", 1)[1].strip())}',
                re.IGNORECASE | re.MULTILINE
            )
    else:
        # Pattern for just the title
        pattern = re.compile(re.escape(section_title), re.IGNORECASE | re.MULTILINE)
    
    # Find the section start
    section_match = pattern.search(html_content)
    if not section_match:
        logger.warning(f"Could not find section header for: {section_title}")
        return {'content': [], 'subsections': []}
    
    # Find the next section start (look for next Item X pattern)
    next_section_pattern = re.compile(r'Item\s+\d+[A-Z]?\s*\.', re.IGNORECASE | re.MULTILINE)
    next_section_match = next_section_pattern.search(html_content, section_match.end())
    
    # Extract content between current section and next section
    if next_section_match:
        section_content = html_content[section_match.start():next_section_match.start()]
    else:
        section_content = html_content[section_match.start():]
    
    # Parse the section content with BeautifulSoup
    section_soup = BeautifulSoup(section_content, 'html.parser')
    
    # First, try to find the main content div
    main_content = None
    for div in section_soup.find_all('div'):
        if 'class' in div.attrs and any(cls in div['class'] for cls in ['content', 'text', 'main']):
            main_content = div
            break
    
    # If we found a main content div, use that
    if main_content:
        section_soup = main_content
    
    # Extract all text elements
    current_subsection = None
    
    # Process all elements in order
    for element in section_soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div']):
        # Skip navigation elements and page headings
        if any(marker in element.get_text().lower() for marker in [
            'table of contents', 'next page', 'previous page',
            'form 10-k', 'form 10-q', 'form 8-k', '|', 'page'
        ]):
            continue
        
        # Get the text content
        text = element.get_text(strip=True)
        if not text:
            continue
        
        # Skip very short text that's likely just formatting
        if len(text.split()) < 3:
            continue
        
        # Check if this is a subsection header
        is_subsection = (
            element.name in ['h3', 'h4', 'h5', 'h6'] or
            (len(text.split()) <= 6 and text.endswith(':')) or
            re.match(r'^[A-Z][A-Za-z\s]{2,}[.:]', text) or
            re.match(r'^[A-Z][A-Za-z\s]{2,}\s*$', text)  # Also match headers without punctuation
        )
        
        if is_subsection:
            # If we have a current subsection, add it to subsections
            if current_subsection and current_subsection['content']:
                subsections.append(current_subsection)
            
            # Start a new subsection
            current_subsection = {
                'title': text,
                'content': []
            }
        else:
            # Skip common elements we don't want
            if not any(skip in text.lower() for skip in [
                'forward-looking statement',
                'table of contents',
                'documents incorporated by reference',
                'part ii',
                'part iii',
                'part iv'
            ]):
                # Clean up the text
                text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
                text = text.strip()
                
                # Add as regular text content
                text_content = {
                    'type': 'text',
                    'content': text
                }
                
                if current_subsection:
                    current_subsection['content'].append(text_content)
                else:
                    content.append(text_content)
    
    # Add the last subsection if it exists
    if current_subsection and current_subsection['content']:
        subsections.append(current_subsection)
    
    # Clean up content
    content = clean_content(content)
    subsections = clean_subsections(subsections)
    
    # If we found no content, try a more aggressive approach
    if not content and not subsections:
        logger.info("No content found with standard approach, trying aggressive extraction")
        # Try to find the section by looking for the title in the HTML
        section_elements = section_soup.find_all(['p', 'div'])
        for element in section_elements:
            text = element.get_text(strip=True)
            if text and len(text.split()) > 3:
                content.append({
                    'type': 'text',
                    'content': text
                })
    
    return {
        'content': content,
        'subsections': subsections
    }

def clean_content(content: List[str]) -> List[str]:
    """Clean and deduplicate content."""
    # Remove very short or empty content
    content = [c for c in content if len(c.split()) > 3]
    
    # Remove duplicate paragraphs
    unique_content = []
    seen = set()
    for c in content:
        # Normalize text for comparison
        normalized = ' '.join(c.split())
        if normalized not in seen:
            seen.add(normalized)
            unique_content.append(c)
    
    return unique_content

def clean_subsections(subsections: List[Dict]) -> List[Dict]:
    """Clean and deduplicate subsections."""
    cleaned = []
    seen_titles = set()
    
    for subsection in subsections:
        # Skip empty subsections
        if not subsection['content']:
            continue
        
        # Normalize title
        title = ' '.join(subsection['title'].split())
        if title not in seen_titles:
            seen_titles.add(title)
            subsection['content'] = clean_content(subsection['content'])
            if subsection['content']:  # Only add if there's content after cleaning
                cleaned.append(subsection)
    
    return cleaned 