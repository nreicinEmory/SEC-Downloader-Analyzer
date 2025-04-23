"""
Module for processing SEC filings into sections and extracting key information.
"""

import re
import logging
from bs4 import BeautifulSoup, Tag
from typing import Dict, List, Optional, Any, Tuple
from .types import RedFlag, SemanticElement
import streamlit as st
from textblob import TextBlob

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_table_of_contents(elements: List['SemanticElement']) -> List[Dict]:
    """Parse the table of contents and document content to create a hierarchical structure."""
    logger.info("Starting table of contents parsing")
    structure = []
    
    # Find the table of contents section
    toc_pattern = re.compile(r'table\s+of\s+contents', re.IGNORECASE)
    toc_section = None
    
    # Look for the table of contents in various possible locations
    for element in elements:
        if element.type in ['heading', 'text'] and toc_pattern.search(element.text):
            toc_section = element
            break
    
    if not toc_section:
        logger.warning("Could not find table of contents section")
        return []
    
    # Find all items in the table of contents
    current_part = None
    current_items = []
    
    # Look for items in the table of contents
    for element in elements:
        text = element.text.strip()
        
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
        if element.type == 'heading' and not re.match(r'^part\s+[iIvV]+$', text, re.IGNORECASE):
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
            section_content = find_section_content(elements, item['title'])
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
    risks, risk_summary = analyze_company_risks(elements)
    focus_analysis = analyze_company_focus(elements)
    
    result = {
        'document_structure': document_structure,
        'risks': risks,
        'risk_summary': risk_summary,
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

def find_section_content(elements: List['SemanticElement'], section_title: str) -> Dict:
    """Find the content and subsections of a given section."""
    logger.info(f"Finding content for section: {section_title}")
    content = []
    subsections = []
    
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
    section_start = None
    for i, element in enumerate(elements):
        if pattern.search(element.text):
            section_start = i
            break
    
    if section_start is None:
        logger.warning(f"Could not find section header for: {section_title}")
        return {'content': [], 'subsections': []}
    
    # Find the next section start (look for next Item X pattern)
    next_section_pattern = re.compile(r'Item\s+\d+[A-Z]?\s*\.', re.IGNORECASE | re.MULTILINE)
    section_end = None
    for i in range(section_start + 1, len(elements)):
        if next_section_pattern.search(elements[i].text):
            section_end = i
            break
    
    # Extract content between current section and next section
    section_elements = elements[section_start:section_end] if section_end else elements[section_start:]
    
    # Process all elements in order
    current_subsection = None
    
    for element in section_elements:
        # Skip navigation elements and page headings
        if any(marker in element.text.lower() for marker in [
            'table of contents', 'next page', 'previous page',
            'form 10-k', 'form 10-q', 'form 8-k', '|', 'page'
        ]):
            continue
        
        # Get the text content
        text = element.text.strip()
        if not text:
            continue
        
        # Skip very short text that's likely just formatting
        if len(text.split()) < 3:
            continue
        
        # Check if this is a subsection header
        is_subsection = (
            element.type == 'heading' or
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
    
    # Clean up content and subsections
    # Remove very short or empty content
    content = [c for c in content if len(c['content'].split()) > 3]
    
    # Remove duplicate paragraphs
    unique_content = []
    seen = set()
    for c in content:
        # Normalize text for comparison
        normalized = ' '.join(c['content'].split())
        if normalized not in seen:
            seen.add(normalized)
            unique_content.append(c)
    
    # Clean subsections
    cleaned_subsections = []
    seen_titles = set()
    
    for subsection in subsections:
        # Skip empty subsections
        if not subsection['content']:
            continue
        
        # Normalize title
        title = ' '.join(subsection['title'].split())
        if title not in seen_titles:
            seen_titles.add(title)
            # Clean subsection content
            subsection_content = []
            seen_content = set()
            for c in subsection['content']:
                normalized = ' '.join(c['content'].split())
                if normalized not in seen_content and len(normalized.split()) > 3:
                    seen_content.add(normalized)
                    subsection_content.append(c)
            
            if subsection_content:  # Only add if there's content after cleaning
                subsection['content'] = subsection_content
                cleaned_subsections.append(subsection)
    
    # If we found no content, try a more aggressive approach
    if not unique_content and not cleaned_subsections:
        logger.info("No content found with standard approach, trying aggressive extraction")
        # Try to find the section by looking for the title in the elements
        for element in section_elements:
            text = element.text.strip()
            if text and len(text.split()) > 3:
                unique_content.append({
                    'type': 'text',
                    'content': text
                })
    
    return {
        'content': unique_content,
        'subsections': cleaned_subsections
    }

def analyze_company_risks(elements: List['SemanticElement']) -> Tuple[List[RedFlag], List[Dict]]:
    """Comprehensive analysis of company risks focusing on investor-relevant categories."""
    logger.info("Starting investor-focused risk analysis")
    risks = []
    processed_contexts = []
    
    # Define investor-relevant risk categories with specific terms and context requirements
    risk_categories = {
        'Major Lawsuits': {
            'terms': [
                # Active litigation
                'lawsuit filed', 'litigation pending', 'ongoing litigation',
                'current lawsuit', 'active litigation', 'pending lawsuit',
                # Specific types
                'securities class action filed', 'shareholder derivative filed',
                'antitrust lawsuit filed', 'patent infringement filed',
                'regulatory enforcement action', 'sec enforcement proceeding',
                # Original terms
                'securities class action', 'securities fraud', 'shareholder class action',
                'stockholder derivative', 'securities violation', 'insider trading',
                'securities litigation', 'securities claim', 'securities lawsuit',
                'sec investigation', 'sec enforcement', 'regulatory investigation',
                'regulatory action', 'enforcement proceeding', 'regulatory violation',
                'compliance issue', 'regulatory penalty', 'regulatory fine',
                'regulatory settlement', 'regulatory order', 'regulatory finding',
                'antitrust investigation', 'antitrust lawsuit', 'monopoly',
                'anti-competitive', 'price fixing', 'market allocation',
                'antitrust violation', 'competition law', 'market power',
                'material litigation', 'significant lawsuit', 'major legal proceeding',
                'substantial claim', 'material claim', 'material legal matter',
                'legal proceeding', 'lawsuit', 'litigation', 'legal action',
                'class action', 'breach of contract', 'dispute', 'arbitration'
            ],
            'required_context': [
                'filed', 'pending', 'ongoing', 'current', 'active',
                'material', 'significant', 'substantial', 'major',
                'damages', 'penalty', 'fine', 'settlement', 'judgment',
                'adverse', 'negative', 'unfavorable', 'damages',
                'penalty', 'fine', 'settlement', 'judgment',
                'could', 'may', 'might', 'will', 'would', 'should'
            ]
        },
        'Auditor Opinions': {
            'terms': [
                # Adverse opinions
                'adverse opinion', 'qualified opinion', 'going concern',
                'material weakness', 'significant deficiency', 'internal control',
                'accounting irregularity', 'restatement', 'material misstatement',
                'audit committee', 'independent auditor', 'audit opinion',
                'audit report', 'auditor resignation', 'auditor change',
                'internal control', 'financial reporting', 'accounting policy',
                'accounting estimate', 'accounting principle', 'accounting standard',
                'financial statement', 'financial reporting', 'financial control'
            ],
            'required_context': [
                'adverse', 'qualified', 'material weakness', 'significant deficiency',
                'going concern', 'restatement', 'irregularity', 'resignation',
                'change', 'replacement', 'termination', 'dismissal',
                'could', 'may', 'might', 'will', 'would', 'should'
            ]
        },
        'Management Changes': {
            'terms': [
                # Executive departures
                'ceo departure', 'cfo departure', 'chief executive officer',
                'chief financial officer', 'executive officer', 'key executive',
                'executive departure', 'executive resignation', 'executive termination',
                'executive change', 'executive transition', 'executive succession',
                # Board changes
                'board member', 'director resignation', 'board resignation',
                'independent director', 'audit committee member', 'board change',
                'board transition', 'board succession', 'board departure',
                # Management structure
                'management change', 'leadership change', 'organizational change',
                'reporting structure', 'management team', 'executive team',
                'management transition', 'leadership transition', 'organizational transition',
                # Termination indicators
                'termination', 'resignation', 'departure', 'separation',
                'for cause', 'without cause', 'good reason', 'constructive termination'
            ],
            'required_context': [
                'resignation', 'departure', 'termination', 'separation',
                'change', 'replacement', 'succession', 'transition',
                'interim', 'temporary', 'acting', 'permanent',
                'could', 'may', 'might', 'will', 'would', 'should'
            ]
        },
        'Cybersecurity & Data Privacy': {
            'terms': [
                # Security incidents
                'data breach', 'security breach', 'cyber attack',
                'hacking incident', 'unauthorized access', 'data theft',
                # Privacy issues
                'privacy violation', 'data privacy', 'personal information',
                'customer data', 'user data', 'member data',
                # System issues
                'system failure', 'service disruption', 'outage',
                'system compromise', 'security vulnerability'
            ],
            'required_context': [
                'material', 'significant', 'substantial', 'major',
                'adverse', 'negative', 'unfavorable', 'damage',
                'impact', 'effect', 'consequence', 'result'
            ]
        },
        'Related Party Transactions': {
            'terms': [
                # Explicit relationships
                'related party transaction', 'related person transaction',
                'insider transaction', 'executive transaction',
                'director transaction', 'board member transaction',
                # Specific relationships
                'family member', 'immediate family', 'close family',
                'executive', 'director', 'officer', 'board member',
                'key employee', 'principal shareholder',
                # Original terms
                'affiliate transaction', 'insider transaction', 'executive transaction',
                'director transaction', 'board member transaction', 'officer transaction',
                'related party', 'related person', 'affiliate', 'insider',
                'business relationship', 'personal relationship', 'financial relationship',
                'family relationship', 'personal interest', 'business interest',
                'purchase', 'sale', 'lease', 'loan', 'guarantee',
                'indemnification', 'compensation', 'benefit', 'arrangement',
                'transaction', 'agreement', 'contract', 'arrangement'
            ],
            'required_context': [
                'material', 'significant', 'substantial', 'major',
                'unusual', 'non-arm\'s length', 'conflict of interest',
                'independence', 'approval', 'review', 'disclosure',
                'transaction', 'agreement', 'contract', 'arrangement',
                'could', 'may', 'might', 'will', 'would', 'should',
                'related party', 'related person', 'affiliate', 'insider',
                'family member', 'executive', 'director', 'officer',
                'board member', 'key employee', 'principal shareholder'
            ]
        },
        'Financial Performance': {
            'terms': [
                # Revenue issues
                'revenue decline', 'sales decline', 'profit decline',
                'earnings decline', 'income decline', 'margin erosion',
                # Financial problems
                'loss', 'deficit', 'impairment', 'write-down',
                'write-off', 'restructuring charge', 'goodwill impairment',
                # Liquidity issues
                'liquidity', 'working capital', 'cash flow',
                'debt covenant', 'credit facility', 'borrowing base',
                # Original terms
                'profit margin', 'gross margin', 'operating margin',
                'revenue', 'sales', 'profit', 'earnings', 'income',
                'margin', 'profitability', 'earnings per share',
                'cash', 'liquidity', 'working capital', 'capital',
                'debt', 'credit', 'borrowing', 'financing',
                'material change', 'significant change', 'substantial change',
                'material impact', 'significant impact', 'substantial impact',
                'change', 'impact', 'effect', 'influence', 'consequence',
                'impairment', 'write-down', 'write-off', 'restructuring'
            ],
            'required_context': [
                'material', 'significant', 'substantial', 'major',
                'adverse', 'negative', 'unfavorable', 'decline',
                'decrease', 'reduction', 'deterioration', 'weakening',
                'percent', '%', 'million', 'billion', 'dollar',
                'could', 'may', 'might', 'will', 'would', 'should'
            ]
        },
        'Competition': {
            'terms': [
                # Market position
                'market share loss', 'competitive position loss',
                'market position loss', 'competitive disadvantage',
                # Customer impact
                'customer loss', 'customer defection', 'customer retention',
                'customer concentration', 'key customer loss',
                # Product issues
                'product obsolescence', 'technological change',
                'disruptive technology', 'new entrant', 'substitute product',
                # Original terms
                'market share', 'competitive position', 'market position',
                'competitive pressure', 'pricing pressure', 'market competition',
                'market', 'competition', 'competitive', 'pricing',
                'customer', 'client', 'buyer', 'purchaser', 'consumer',
                'customer base', 'customer relationship', 'customer service',
                'product', 'technology', 'innovation', 'development',
                'research', 'r&d', 'patent', 'intellectual property',
                'industry change', 'market change', 'competitive landscape',
                'competitive environment', 'market disruption', 'industry disruption',
                'industry', 'market', 'sector', 'business', 'commercial'
            ],
            'required_context': [
                'material', 'significant', 'substantial', 'major',
                'adverse', 'negative', 'unfavorable', 'decline',
                'decrease', 'reduction', 'deterioration', 'weakening',
                'competitor', 'competition', 'competitive', 'market',
                'could', 'may', 'might', 'will', 'would', 'should'
            ]
        }
    }
    
    def has_negative_sentiment(text: str) -> bool:
        """Check if the text has negative sentiment with a more balanced threshold."""
        sentiment = TextBlob(text).sentiment.polarity
        return sentiment < -0.2  # More balanced threshold for negative sentiment
    
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
    
    # Process all elements for risks
    for element in elements:
        # Skip empty elements and tables
        if not element.text or element.type == 'table':
            continue
            
        text = element.text.lower()
        
        # Process each category
        for category, config in risk_categories.items():
            for term in config['terms']:
                if term in text:
                    # Get the full text as context
                    context = element.text.strip()
                    
                    # Skip if context is too short or already processed
                    if len(context.split()) < 5 or is_duplicate_or_contained(context, processed_contexts):
                        continue
                    
                    # Check for required context terms
                    if not any(context_term in text for context_term in config['required_context']):
                        continue
                        
                    # Only flag if the context has negative sentiment
                    if has_negative_sentiment(context):
                        processed_contexts.append(context)
                        
                        # Determine severity based on sentiment and context
                        sentiment = TextBlob(context).sentiment.polarity
                        severity = 'High' if sentiment < -0.4 else 'Medium'  # More balanced threshold for High severity
                        
                        # Check for additional severity indicators
                        severity_indicators = [
                            'material', 'significant', 'substantial', 'major',
                            'critical', 'important', 'key', 'essential', 'fundamental',
                            'adverse', 'serious', 'severe', 'material adverse effect',
                            'could', 'may', 'might', 'will', 'would', 'should',
                            'risk', 'uncertainty', 'challenge', 'threat', 'concern',
                            'issue', 'problem', 'difficulty', 'obstacle', 'barrier'
                        ]
                        
                        if any(indicator in text for indicator in severity_indicators):
                            severity = 'High'
                        
                        risks.append(RedFlag(
                            category=category,
                            description=f"Potential {category} risk related to {term}",
                            severity=severity,
                            context=context
                        ))
                        logger.info(f"Found {severity} risk in category {category}: {term}")
    
    # Create summary by category
    summary = []
    for category in risk_categories.keys():
        category_risks = [r for r in risks if r.category == category]
        high_severity = len([r for r in category_risks if r.severity == 'High'])
        medium_severity = len([r for r in category_risks if r.severity == 'Medium'])
        
        if category_risks:
            summary.append({
                'category': category,
                'high_severity_count': high_severity,
                'medium_severity_count': medium_severity,
                'risks': category_risks
            })
    
    # Sort risks by severity (High first, then Medium)
    risks.sort(key=lambda x: 0 if x.severity == 'High' else 1)
    
    logger.info(f"Risk analysis complete. Found {len(risks)} risks across {len(summary)} categories")
    return risks, summary

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