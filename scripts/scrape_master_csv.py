#!/usr/bin/env python3
"""
Scrape all products from master CSV file
Separates Amazon and Hamleys products and runs appropriate scrapers
"""

import csv
import json
import sys
import os
from collections import defaultdict
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scrape_from_csv import scrape_products_from_csv as scrape_amazon_from_csv
from scrape_hamleys_from_csv import scrape_products_from_csv as scrape_hamleys_from_csv


def extract_unique_products(csv_file):
    """Extract unique product links with categories and tags from master CSV."""
    products = {}
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get('Product link', '').strip()
            if not url:
                continue
            
            # Get category and tags
            category = row.get('Product Category', '').strip()
            tags = row.get('Tags', '').strip()
            
            # Only keep first occurrence (unique products)
            if url not in products:
                products[url] = {
                    'category': category,
                    'tags': tags,
                }
    
    return products


def separate_products(products):
    """Separate products into Amazon and Hamleys."""
    amazon_products = {}
    hamleys_products = {}
    
    for url, data in products.items():
        if 'amazon.in' in url or 'amazon.com' in url:
            amazon_products[url] = data
        elif 'hamleys.in' in url:
            hamleys_products[url] = data
        else:
            print(f"Unknown source for URL: {url}")
    
    return amazon_products, hamleys_products


def create_temp_csv(products, filename):
    """Create a temporary CSV file for scraping."""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Product link', 'Product Category', 'Tags (seprated by comma)'])
        for url, data in products.items():
            writer.writerow([url, data['category'], data['tags']])


def main():
    master_csv = 'TLM products list master - Copy of TLM products list master.csv'
    
    if len(sys.argv) > 1:
        master_csv = sys.argv[1]
    
    print(f"Reading master CSV: {master_csv}")
    print("="*80)
    
    # Extract unique products
    products = extract_unique_products(master_csv)
    print(f"Found {len(products)} unique products")
    
    # Separate by source
    amazon_products, hamleys_products = separate_products(products)
    print(f"Amazon products: {len(amazon_products)}")
    print(f"Hamleys products: {len(hamleys_products)}")
    print("="*80)
    
    all_results = []
    
    # Scrape Amazon products
    if amazon_products:
        print("\nScraping Amazon products...")
        print("="*80)
        temp_amazon_csv = 'temp_amazon_products.csv'
        create_temp_csv(amazon_products, temp_amazon_csv)
        
        try:
            amazon_results = scrape_amazon_from_csv(temp_amazon_csv, 'temp_amazon_results.json')
            all_results.extend(amazon_results)
        except Exception as e:
            print(f"Error scraping Amazon products: {e}")
        finally:
            # Clean up temp file
            if os.path.exists(temp_amazon_csv):
                os.remove(temp_amazon_csv)
    
    # Scrape Hamleys products
    if hamleys_products:
        print("\nScraping Hamleys products...")
        print("="*80)
        temp_hamleys_csv = 'temp_hamleys_products.csv'
        create_temp_csv(hamleys_products, temp_hamleys_csv)
        
        try:
            hamleys_results = scrape_hamleys_from_csv(temp_hamleys_csv, 'temp_hamleys_results.json', limit=None)
            all_results.extend(hamleys_results)
        except Exception as e:
            print(f"Error scraping Hamleys products: {e}")
        finally:
            # Clean up temp file
            if os.path.exists(temp_hamleys_csv):
                os.remove(temp_hamleys_csv)
    
    # Save combined results
    output_json = 'data/results/master_scrape_results.json'
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*80)
    print(f"Scraped {len(all_results)} products total")
    print(f"Results saved to: {output_json}")
    
    successful = sum(1 for r in all_results if 'error' not in r)
    failed = len(all_results) - successful
    print(f"Successful: {successful}, Failed: {failed}")
    
    return all_results


if __name__ == '__main__':
    main()

