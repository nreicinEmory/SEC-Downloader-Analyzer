"""
Module for downloading SEC filings.
"""

from sec_downloader import Downloader

def download_filing(ticker: str, form_type: str) -> str:
    """Download a filing and return its HTML content."""
    dl = Downloader("SEC Analyzer", "noah.reicin@emory.edu")
    return dl.get_filing_html(ticker=ticker, form=form_type) 