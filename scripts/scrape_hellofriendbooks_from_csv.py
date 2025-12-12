#!/usr/bin/env python3
"""
Scrape Hello Friend Books products from CSV file and include tags/categories
"""

import csv
import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scrapers.hellofriendbooks_scraper import scrape_hellofriendbooks_product


def scrape_products_from_csv(csv_file, output_json='hellofriendbooks_scrape_results.json', limit=None):
    """Read CSV file and scrape Hello Friend Books products."""
    
    products_data = {}
    
    # Read CSV to get URLs, categories, and tags
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if limit and idx >= limit:
                break
            url = row.get('Product link', '').strip()
            category = row.get('Product Category', '').strip()
            tags = row.get('Tags (seprated by comma)', '').strip()
            
            if url:
                products_data[url] = {
                    'category': category,
                    'tags': tags,
                }
    
    print(f"Found {len(products_data)} products in CSV file")
    if limit:
        print(f"Limiting to first {limit} products")
    print("Starting to scrape...\n")
    
    results = []
    urls = list(products_data.keys())
    
    for idx, url in enumerate(urls, 1):
        print(f"[{idx}/{len(urls)}] ", end='')
        result = scrape_hellofriendbooks_product(url)
        
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
    csv_file = 'data/input/TLM_products_hellofriendbooks.csv'
    output_json = 'data/results/hellofriendbooks_scrape_results.json'
    limit = None  # Scrape all products by default
    
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_json = sys.argv[2]
    if len(sys.argv) > 3:
        limit = int(sys.argv[3]) if sys.argv[3].isdigit() else None
    
    scrape_products_from_csv(csv_file, output_json, limit)
