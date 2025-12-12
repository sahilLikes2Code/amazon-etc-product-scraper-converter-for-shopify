#!/usr/bin/env python3
"""
Scrape Amazon products from CSV file and include tags/categories
"""

import csv
import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scrapers.amazon_scraper import scrape_amazon_product


def scrape_products_from_csv(csv_file, output_json='amazon_scrape_results.json'):
    """Read CSV file and scrape all Amazon products."""
    
    products_data = {}
    
    # Read CSV to get URLs, categories, and tags
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get('Product link', '').strip()
            category = row.get('Product Category', '').strip()
            tags = row.get('Tags (seprated by comma)', '').strip()
            
            if url:
                products_data[url] = {
                    'category': category,
                    'tags': tags,
                }
    
    print(f"Found {len(products_data)} products in CSV file")
    print("Starting to scrape...\n")
    
    results = []
    urls = list(products_data.keys())
    
    for idx, url in enumerate(urls, 1):
        print(f"[{idx}/{len(urls)}] ", end='')
        result = scrape_amazon_product(url)
        
        # Add category and tags from CSV
        if url in products_data:
            result['category'] = products_data[url]['category']
            result['tags'] = products_data[url]['tags']
        
        results.append(result)
        print()  # New line after each product
    
    # Save results
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nScraped {len(results)} products")
    print(f"Results saved to: {output_json}")
    
    # Print summary
    successful = sum(1 for r in results if 'error' not in r)
    failed = len(results) - successful
    print(f"Successful: {successful}, Failed: {failed}")
    
    return results


if __name__ == '__main__':
    csv_file = 'data/input/TLM_products_amazon.csv'
    output_json = 'data/results/amazon_scrape_results.json'
    
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_json = sys.argv[2]
    
    scrape_products_from_csv(csv_file, output_json)

