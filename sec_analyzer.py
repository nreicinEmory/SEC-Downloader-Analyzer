#!/usr/bin/env python3
"""
Main script for analyzing SEC filings.
"""

import argparse
import json
from typing import Dict, Any
from datetime import datetime

from sec_analyzer.downloader import SECDownloader
from sec_analyzer.financial_metrics import RawFinancialData, FinancialMetricsCalculator
from sec_analyzer.anomaly_detector import AnomalyDetector

def analyze_company(ticker: str, api_key: str = None) -> Dict[str, Any]:
    """
    Analyze a company's SEC filings.
    
    Args:
        ticker: Company ticker symbol
        api_key: SEC API key (optional)
        
    Returns:
        Dictionary containing analysis results
    """
    # Initialize components
    downloader = SECDownloader(api_key)
    raw_data = RawFinancialData()
    metrics_calculator = FinancialMetricsCalculator(raw_data)
    anomaly_detector = AnomalyDetector()
    
    # Get recent filings
    filings = downloader.get_filings(ticker, form_type="10-K", limit=5)
    if not filings:
        raise ValueError(f"No 10-K filings found for {ticker}")
    
    # Process each filing
    results = {
        'ticker': ticker,
        'analysis_date': datetime.now().isoformat(),
        'filings': []
    }
    
    for filing in filings:
        filing_data = {
            'filing_date': filing['filedAt'],
            'form_type': filing['formType'],
            'url': filing['url']
        }
        
        # Download and process filing
        filing_text, sections = downloader.download_filing(filing['url'])
        filing_data['sections'] = list(sections.keys())
        
        # Analyze financial statements section
        if 'financial_statements' in sections:
            financial_text = '\n'.join(sections['financial_statements'])
            metrics = metrics_calculator.calculate_metrics(financial_text)
            filing_data['metrics'] = metrics
            
            # Calculate financial ratios
            ratios = metrics_calculator.calculate_ratios(metrics)
            filing_data['ratios'] = ratios
        
        # Analyze management discussion section
        if 'management_discussion' in sections:
            mda_text = '\n'.join(sections['management_discussion'])
            # Perform NLP analysis
            sentiment = nlp_analyzer.analyze_sentiment(mda_text)
            key_phrases = nlp_analyzer.extract_key_phrases(mda_text)
            risk_factors = nlp_analyzer.detect_risk_factors(mda_text)
            tone = nlp_analyzer.analyze_tone(mda_text)
            forward_statements = nlp_analyzer.extract_forward_looking_statements(mda_text)
            
            filing_data['mda_analysis'] = {
                'sentiment': sentiment,
                'key_phrases': key_phrases,
                'risk_factors': risk_factors,
                'tone': tone,
                'forward_statements': forward_statements
            }
        
        # Analyze risk factors section
        if 'risk_factors' in sections:
            risk_text = '\n'.join(sections['risk_factors'])
            risk_analysis = nlp_analyzer.detect_risk_factors(risk_text)
            filing_data['risk_analysis'] = risk_analysis
        
        # Detect anomalies
        historical_metrics = [f['metrics'] for f in results['filings'] if 'metrics' in f]
        financial_anomalies = anomaly_detector.detect_financial_anomalies(metrics, historical_metrics)
        ratio_anomalies = anomaly_detector.detect_ratio_anomalies(ratios)
        risk_anomalies = anomaly_detector.detect_risk_anomalies(risk_factors)
        sentiment_anomalies = anomaly_detector.detect_sentiment_anomalies(sentiment)
        
        # Combine all anomalies
        all_anomalies = anomaly_detector.combine_anomalies(
            financial_anomalies,
            ratio_anomalies,
            risk_anomalies,
            sentiment_anomalies
        )
        
        filing_data['anomalies'] = all_anomalies
        results['filings'].append(filing_data)
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Analyze SEC filings for a company')
    parser.add_argument('--ticker', required=True, help='Company ticker symbol')
    parser.add_argument('--api-key', help='SEC API key (optional if set in .env file)')
    parser.add_argument('--output', help='Output file path (optional)')
    
    args = parser.parse_args()
    
    try:
        results = analyze_company(args.ticker, args.api_key)
        
        # Print results
        print("\nAnalysis Results:")
        print(f"Company: {results['ticker']}")
        print(f"Analysis Date: {results['analysis_date']}")
        print(f"\nNumber of filings analyzed: {len(results['filings'])}")
        
        # Print key findings from the most recent filing
        latest_filing = results['filings'][0]
        print("\nLatest Filing Analysis:")
        print(f"Filing Date: {latest_filing['filing_date']}")
        print(f"Sections found: {', '.join(latest_filing['sections'])}")
        
        if 'metrics' in latest_filing:
            print("\nKey Financial Metrics:")
            for metric, value in latest_filing['metrics'].items():
                print(f"{metric.replace('_', ' ').title()}: ${value:,.2f}")
        
        if 'ratios' in latest_filing:
            print("\nFinancial Ratios:")
            for ratio, value in latest_filing['ratios'].items():
                print(f"{ratio.replace('_', ' ').title()}: {value:.2%}")
        
        if 'mda_analysis' in latest_filing:
            print("\nManagement Discussion Analysis:")
            sentiment = latest_filing['mda_analysis']['sentiment']
            print(f"Sentiment: {sentiment['polarity']:.2f} (polarity), {sentiment['subjectivity']:.2f} (subjectivity)")
            
            print("\nKey Phrases:")
            for phrase, score in latest_filing['mda_analysis']['key_phrases'][:5]:
                print(f"- {phrase} ({score:.2f})")
        
        if 'anomalies' in latest_filing and latest_filing['anomalies']:
            print("\nDetected Anomalies/Red Flags:")
            for anomaly, details in latest_filing['anomalies'].items():
                if 'message' in details:
                    print(f"- {details['message']}")
        
        # Save results to file if specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to {args.output}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main()) 