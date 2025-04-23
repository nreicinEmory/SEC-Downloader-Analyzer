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

### Financial Analysis
- **Balance Sheet Analysis**: Comprehensive view of assets, liabilities, and equity
- **Income Statement Analysis**: Revenue, expenses, and profitability metrics
- **Cash Flow Analysis**: Operating, investing, and financing activities
- **Financial Ratios**:
  - Efficiency Ratios: Asset turnover, inventory turnover
  - Liquidity Ratios: Current ratio, quick ratio
  - Profitability Ratios: Gross margin, net margin, ROE
  - Solvency Ratios: Debt-to-equity, interest coverage
  - Valuation Ratios: P/E ratio, P/B ratio

### SEC Filing Analysis
- Downloads SEC filings using the SEC EDGAR system
- Extracts and analyzes key sections:
  - Management Discussion & Analysis (MD&A)
  - Risk Factors
  - Financial Statements
  - Notes to Financial Statements
- Identifies potential red flags and risk factors
- Analyzes company focus areas and strategic priorities

### Data Visualization
- Interactive charts for financial metrics
- Trend analysis and comparative views
- Document structure visualization
- Risk factor categorization and severity assessment

## Project Structure

- `app.py`: Main Streamlit application
- `sec_analyzer/`: Core analysis module
  - `downloader.py`: Handles SEC filing downloads with rate limiting
  - `semantic_processor.py`: Processes and analyzes filings
  - `fin_ratios.py`: Financial metrics and ratio calculations
  - `types.py`: Data structures and type definitions

## Dependencies

- Python 3.8+
- Key Dependencies:
  - `financetoolkit`: Financial data and ratio calculations
  - `sec-downloader`: SEC EDGAR system integration
  - `streamlit`: Web interface
  - `pandas` & `numpy`: Data manipulation
  - `plotly`: Interactive visualizations
  - `beautifulsoup4`: HTML parsing
  - `textblob`: Sentiment analysis
  - `nltk`: Natural language processing

See requirements.txt for complete list of dependencies and versions.

## Financial Data Methodology

The tool uses a comprehensive approach to financial analysis:

1. **Data Collection**:
   - SEC filings through EDGAR system
   - Financial statements and notes
   - Management discussions and risk factors

2. **Financial Metrics**:
   - Standardized financial ratios
   - Industry-specific metrics
   - Trend analysis and comparisons

3. **Risk Assessment**:
   - Financial health indicators
   - Operational risks
   - Market and competitive risks
   - Regulatory compliance

4. **Analysis Features**:
   - Historical trend analysis
   - Peer comparison
   - Industry benchmarking
   - Risk factor identification 