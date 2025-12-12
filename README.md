# Product Scrapers

This directory contains scrapers for extracting product data from various e-commerce sites and converting them to Shopify-compatible CSV format.

## Directory Structure

```
.
├── scrapers/                    # Core scraper modules
│   ├── amazon_scraper.py
│   ├── hamleys_scraper.py
│   ├── harpercollins_scraper.py
│   ├── hellofriendbooks_scraper.py
│   └── convert_to_shopify_csv.py
│
├── scripts/                     # Scripts to run scrapers from CSV files
│   ├── scrape_from_csv.py              # Amazon
│   ├── scrape_hamleys_from_csv.py
│   ├── scrape_harpercollins_from_csv.py
│   └── scrape_hellofriendbooks_from_csv.py
│
├── data/
│   ├── input/                   # Input CSV files with product links
│   │   ├── TLM_products_amazon.csv
│   │   ├── TLM_products_hamleys.csv
│   │   ├── TLM_products_harpercollins.csv
│   │   └── TLM_products_hellofriendbooks.csv
│   │
│   ├── results/                  # JSON results from scraping
│   │   ├── amazon_scrape_results.json
│   │   ├── hamleys_scrape_results.json
│   │   ├── harpercollins_scrape_results.json
│   │   └── hellofriendbooks_scrape_results.json
│   │
│   └── shopify/                  # Final Shopify CSV files
│       ├── amazon_shopify_import.csv
│       ├── hamleys_shopify_import.csv
│       ├── harpercollins_shopify_import.csv
│       └── hellofriendbooks_shopify_import.csv
│
└── requirements.txt             # Python dependencies
```

## Usage

### Setup

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running Scrapers

#### Amazon Products
```bash
python scripts/scrape_from_csv.py data/input/TLM_products_amazon.csv data/results/amazon_scrape_results.json
python scrapers/convert_to_shopify_csv.py data/results/amazon_scrape_results.json data/shopify/amazon_shopify_import.csv
```

#### Hamleys Products
```bash
python scripts/scrape_hamleys_from_csv.py data/input/TLM_products_hamleys.csv data/results/hamleys_scrape_results.json
python scrapers/convert_to_shopify_csv.py data/results/hamleys_scrape_results.json data/shopify/hamleys_shopify_import.csv
```

#### HarperCollins Products
```bash
python scripts/scrape_harpercollins_from_csv.py data/input/TLM_products_harpercollins.csv data/results/harpercollins_scrape_results.json
python scrapers/convert_to_shopify_csv.py data/results/harpercollins_scrape_results.json data/shopify/harpercollins_shopify_import.csv
```

#### Hello Friend Books Products
```bash
python scripts/scrape_hellofriendbooks_from_csv.py data/input/TLM_products_hellofriendbooks.csv data/results/hellofriendbooks_scrape_results.json
python scrapers/convert_to_shopify_csv.py data/results/hellofriendbooks_scrape_results.json data/shopify/hellofriendbooks_shopify_import.csv
```

## What Each Scraper Extracts

All scrapers extract:
- **Title** - Product title
- **Description** - Product description (formatted as HTML)
- **Price** - Product price in INR (₹)
- **Images** - All product images (filtered to exclude thumbnails/related products)
- **Category** - From CSV input
- **Tags** - From CSV input

## Output Format

- **JSON Results**: Raw scraped data saved to `data/results/`
- **Shopify CSV**: Formatted for Shopify import, saved to `data/shopify/`

Each product image creates a separate row in the Shopify CSV (one row per image).
