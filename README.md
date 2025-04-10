# SEC Filing Analyzer

A tool for downloading and analyzing SEC filings, extracting financial metrics, identifying red flags, and analyzing company focus areas.

## Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the Streamlit app:
```bash
streamlit run app.py
```

2. In the web interface:
   - Enter a ticker symbol (e.g., "AAPL")
   - Select a form type (e.g., "10-K")
   - Click "Get Filing" to analyze

## Features

- Downloads SEC filings using the SEC EDGAR system
- Extracts financial metrics and ratios
- Identifies potential red flags
- Analyzes company focus areas
- Visualizes data using interactive charts

## Project Structure

- `app.py`: Main Streamlit application
- `sec_analyzer/`: Core analysis module
  - `downloader.py`: Handles SEC filing downloads
  - `semantic_processor.py`: Processes and analyzes filings
  - `types.py`: Data structures and type definitions
  - `parsing/`: HTML parsing utilities

## Dependencies

- Python 3.8+
- See requirements.txt for full list of dependencies 