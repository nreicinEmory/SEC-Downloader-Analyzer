"""
Module for downloading SEC filings.
"""

import os
from pathlib import Path
from datetime import datetime
from sec_downloader import Downloader
from sec_downloader.types import RequestedFilings

# Use existing cache directory
CACHE_DIR = Path("sec_cache")
CACHE_DIR.mkdir(exist_ok=True)

def get_cache_path(ticker: str, form_type: str, filing_date: str) -> Path:
    """Get the path for a cached filing."""
    # Create company directory
    company_dir = CACHE_DIR / ticker
    company_dir.mkdir(exist_ok=True)
    
    # Create form type directory
    form_dir = company_dir / form_type
    form_dir.mkdir(exist_ok=True)
    
    # Create filename with filing date
    filename = f"{filing_date}.html"
    return form_dir / filename

def download_filing(ticker: str, form_type: str) -> str:
    """Download a filing and return its HTML content."""
    # Initialize downloader
    dl = Downloader("SEC Analyzer", "noah.reicin@emory.edu")
    
    # Get filing metadata
    print(f"Getting filing information for {ticker} ({form_type})...")
    requested_filings = RequestedFilings(ticker_or_cik=ticker, form_type=form_type, limit=1)
    metadatas = dl.get_filing_metadatas(requested_filings)
    
    if not metadatas:
        raise ValueError(f"No {form_type} filings found for {ticker}")
    
    # Get the filing metadata
    metadata = metadatas[0]
    filing_date = metadata.filing_date.replace('-', '')  # Format as YYYYMMDD
    
    # Create cache path with filing date
    cache_path = get_cache_path(ticker, form_type, filing_date)
    
    # Check if file is already cached
    if cache_path.exists():
        print(f"Using cached filing: {cache_path}")
        return cache_path.read_text()
    
    # Download the filing
    print(f"Downloading filing for {ticker} ({form_type}) from {filing_date}...")
    html_content = dl.download_filing(url=metadata.primary_doc_url).decode()
    
    # Cache the content
    cache_path.write_text(html_content)
    print(f"Filing saved to: {cache_path}")
    
    return html_content 