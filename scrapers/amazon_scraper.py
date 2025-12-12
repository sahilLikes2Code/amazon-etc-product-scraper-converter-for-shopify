#!/usr/bin/env python3
"""
Amazon Product Scraper
Extracts title, description, and all images from Amazon product pages.
"""

import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import sys


def extract_asin(url):
    """Extract ASIN from Amazon URL."""
    patterns = [
        r'/dp/([A-Z0-9]{10})',
        r'/product/([A-Z0-9]{10})',
        r'/gp/product/([A-Z0-9]{10})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # Try query parameter
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if 'asin' in params:
        return params['asin'][0]
    
    return None


def get_headers():
    """Return headers to mimic a browser request."""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }


def extract_title(soup):
    """Extract product title from the page."""
    # Try multiple selectors
    selectors = [
        '#productTitle',
        'h1#title span#productTitle',
        'h1.a-size-large',
        'span#productTitle',
        'h1.a-spacing-none',
    ]
    
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            title = element.get_text(strip=True)
            if title:
                return title
    
    # Fallback: look for h1 with title-like content
    h1 = soup.find('h1', {'id': 'title'})
    if h1:
        title_span = h1.find('span', {'id': 'productTitle'})
        if title_span:
            return title_span.get_text(strip=True)
    
    return None


def extract_description(soup):
    """Extract product description from the page."""
    description_parts = []
    
    # Try to find feature bullets (About this item section)
    feature_bullets = soup.find('div', {'id': 'feature-bullets'})
    if feature_bullets:
        bullets = feature_bullets.find_all('span', class_='a-list-item')
        for bullet in bullets:
            text = bullet.get_text(strip=True)
            # Filter out common non-descriptive text
            if text and not any(skip in text.lower() for skip in [
                'make sure', 'see more', 'see less', 'click', 'tap'
            ]):
                description_parts.append(text)
    
    # Try book description expander (common for books)
    book_desc = soup.find('div', {'data-a-expander-name': 'book_description_expander'})
    if book_desc:
        # Get paragraphs
        paragraphs = book_desc.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text and len(text) > 10 and text not in description_parts:
                description_parts.append(text)
        
        # Get list items
        list_items = book_desc.find_all('li')
        for li in list_items:
            text = li.get_text(strip=True)
            if text and len(text) > 5 and text not in description_parts:
                description_parts.append(text)
    
    # Try product description section
    desc_selectors = [
        '#productDescription',
        'div#productDescription_feature_div',
        'div#productDescription_feature_div p',
        'div.a-section.a-spacing-medium p',
        'div[data-a-expander-name="book_description_expander"]',
    ]
    
    for selector in desc_selectors:
        desc_elements = soup.select(selector)
        for element in desc_elements:
            # Skip if already processed
            if element == book_desc:
                continue
            text = element.get_text(strip=True)
            if text and len(text) > 20:  # Filter out short text
                if text not in description_parts:
                    description_parts.append(text)
    
    # Try to find description in iframe content (some products load description in iframe)
    iframe = soup.find('iframe', {'id': 'productDescription_iframe'})
    if iframe:
        iframe_src = iframe.get('src', '')
        if iframe_src:
            try:
                iframe_response = requests.get(iframe_src, headers=get_headers(), timeout=10)
                iframe_soup = BeautifulSoup(iframe_response.content, 'html.parser')
                iframe_paragraphs = iframe_soup.find_all('p')
                for p in iframe_paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 20 and text not in description_parts:
                        description_parts.append(text)
            except:
                pass  # If iframe fails, continue without it
    
    # If we found bullets, join them; otherwise try to get full description
    if description_parts:
        return '\n\n'.join(description_parts)
    
    # Fallback: look for any description-like content
    desc = soup.find('div', {'id': 'productDescription'})
    if desc:
        return desc.get_text(strip=True)
    
    return None


def extract_price(soup):
    """Extract product price from the page."""
    price = None
    compare_at_price = None
    
    # Method 1: Look for price in hidden input fields
    price_input = soup.find('input', {'name': re.compile(r'customerVisiblePrice.*amount', re.I)})
    if price_input:
        try:
            price_value = float(price_input.get('value', ''))
            if price_value:
                price = f"{price_value:.2f}"
        except (ValueError, AttributeError):
            pass
    
    # Method 2: Look for price in a-price-whole class
    price_whole = soup.find('span', class_='a-price-whole')
    if price_whole:
        price_text = price_whole.get_text(strip=True)
        # Remove currency symbols and clean
        price_text = re.sub(r'[^\d.]', '', price_text)
        try:
            price_value = float(price_text)
            if price_value:
                price = f"{price_value:.2f}"
        except (ValueError, AttributeError):
            pass
    
    # Method 3: Look for price in a-offscreen (accessible price)
    offscreen_prices = soup.find_all('span', class_='a-offscreen')
    for offscreen in offscreen_prices:
        text = offscreen.get_text(strip=True)
        # Look for price pattern like ₹271.00
        match = re.search(r'₹?\s*(\d+\.?\d*)', text)
        if match:
            try:
                price_value = float(match.group(1))
                if price_value and not price:  # Only use if we don't have price yet
                    price = f"{price_value:.2f}"
            except (ValueError, AttributeError):
                pass
    
    # Method 4: Look for compare at price (MRP/strikethrough price)
    strike_price = soup.find('span', class_='a-text-price')
    if strike_price:
        strike_text = strike_price.get_text(strip=True)
        match = re.search(r'₹?\s*(\d+\.?\d*)', strike_text)
        if match:
            try:
                compare_value = float(match.group(1))
                if compare_value:
                    compare_at_price = f"{compare_value:.2f}"
            except (ValueError, AttributeError):
                pass
    
    # Method 5: Look in JSON data in scripts
    scripts = soup.find_all('script', type='text/javascript')
    for script in scripts:
        if script.string:
            # Look for price in JSON structures
            match = re.search(r'"priceAmount":\s*(\d+\.?\d*)', script.string)
            if match:
                try:
                    price_value = float(match.group(1))
                    if price_value and not price:
                        price = f"{price_value:.2f}"
                except (ValueError, AttributeError):
                    pass
    
    return {
        'price': price,
        'compare_at_price': compare_at_price,
    }


def extract_images(soup):
    """Extract only main product images (exclude related/recommended products)."""
    images = []
    image_urls = set()
    
    # Method 1: Extract from colorImages JSON data (most reliable - main product gallery)
    # Extract hiRes URLs directly - these are always product images
    scripts = soup.find_all('script', type='text/javascript')
    hi_res_urls = []
    
    for script in scripts:
        if not script.string:
            continue
        
        script_text = script.string
        
        # Only extract hiRes URLs that are within colorImages context
        # Look for the colorImages section first
        color_images_match = re.search(r"'colorImages'|\"colorImages\"", script_text)
        if color_images_match:
            # Extract all hiRes URLs from this script (they're in the colorImages array)
            # Pattern: "hiRes":"URL" or 'hiRes':'URL'
            hi_res_patterns = [
                r'"hiRes"\s*:\s*"([^"]+)"',
                r"'hiRes'\s*:\s*'([^']+)'",
            ]
            
            for pattern in hi_res_patterns:
                hi_res_matches = re.findall(pattern, script_text)
                for url in hi_res_matches:
                    # Only include URLs from media-amazon.com (product images)
                    if url and 'media-amazon.com' in url:
                        # Extract base image ID to avoid duplicates of different sizes
                        # URLs like: .../I/81Zy3A+8MqL._SL1500_.jpg and .../I/81Zy3A+8MqL._SY522_.jpg
                        # Should be treated as the same image, prefer highest quality
                        base_match = re.search(r'/I/([A-Za-z0-9+\-_]+)', url)
                        if base_match:
                            base_id = base_match.group(1)
                            # Prefer _SL1500_ or _SL1200_ (highest quality)
                            if '_SL1500_' in url or '_SL1200_' in url:
                                hi_res_urls.append((base_id, url, 3))  # Priority 3 (highest)
                            elif '_SL' in url:
                                hi_res_urls.append((base_id, url, 2))  # Priority 2
                            else:
                                hi_res_urls.append((base_id, url, 1))  # Priority 1
    
    # Deduplicate by base_id, keeping highest priority
    seen_bases = {}
    for base_id, url, priority in hi_res_urls:
        if base_id not in seen_bases or seen_bases[base_id][1] < priority:
            seen_bases[base_id] = (url, priority)
    
    # Add unique hiRes images
    for url, _ in seen_bases.values():
        if url not in image_urls:
            images.append(url)
            image_urls.add(url)
    
    # Method 2: Extract from main image container only (landingImage and altImages)
    # Find the main image block container
    image_block = soup.find('div', {'id': 'imageBlock'})
    if image_block:
        # Extract from landingImage (main product image) - only if we don't have it from hiRes
        landing_img = image_block.find('img', {'id': 'landingImage'})
        if landing_img:
            # Try data-old-hires first (highest quality)
            hires_url = landing_img.get('data-old-hires', '')
            if hires_url:
                # Extract base ID to check if we already have this image
                base_match = re.search(r'/I/([A-Za-z0-9+\-_]+)', hires_url)
                if base_match:
                    base_id = base_match.group(1)
                    # Only add if we don't already have this image (from hiRes)
                    if base_id not in [re.search(r'/I/([A-Za-z0-9+\-_]+)', url).group(1) 
                                      for url in image_urls if re.search(r'/I/([A-Za-z0-9+\-_]+)', url)]:
                        images.append(hires_url)
                        image_urls.add(hires_url)
    
    # Final deduplication: remove duplicates by base image ID, keeping highest quality
    final_images = []
    seen_bases = {}
    
    for img_url in images:
        base_match = re.search(r'/I/([A-Za-z0-9+\-_]+)', img_url)
        if base_match:
            base_id = base_match.group(1)
            # Determine quality priority
            if '_SL1500_' in img_url or '_SL1200_' in img_url:
                priority = 3
            elif '_SL' in img_url:
                priority = 2
            elif '_SY' in img_url or '_SX' in img_url:
                priority = 1
            else:
                priority = 0
            
            # Keep highest priority version of each base image
            if base_id not in seen_bases or seen_bases[base_id][1] < priority:
                seen_bases[base_id] = (img_url, priority)
    
    # Return unique images in order, highest quality first
    final_images = [url for url, _ in sorted(seen_bases.values(), key=lambda x: x[1], reverse=True)]
    
    return final_images


def scrape_amazon_product(url):
    """Scrape product information from an Amazon URL."""
    print(f"Scraping: {url}")
    
    try:
        response = requests.get(url, headers=get_headers(), timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        price_info = extract_price(soup)
        
        result = {
            'url': url,
            'asin': extract_asin(url),
            'title': extract_title(soup),
            'description': extract_description(soup),
            'price': price_info.get('price'),
            'compare_at_price': price_info.get('compare_at_price'),
            'images': extract_images(soup),
        }
        
        return result
        
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        return {
            'url': url,
            'error': str(e),
        }
    except Exception as e:
        print(f"Error parsing page: {e}")
        return {
            'url': url,
            'error': str(e),
        }


def main():
    """Main function to scrape multiple URLs."""
    urls = [
        'https://www.amazon.in/Booktopus-Torch-Discovery-Book-Interactive/dp/9365697948/ref=pd_bxgy_thbs_d_sccl_1/520-0973998-4577526?pd_rd_w=PKTJc&content-id=amzn1.sym.e933bed8-66b5-4e19-9aeb-b2834144fba3&pf_rd_p=e933bed8-66b5-4e19-9aeb-b2834144fba3&pf_rd_r=SQ4TQXGH9PMCJWE095N7&pd_rd_wg=CRYoK&pd_rd_r=085ad554-fbb9-412a-aaeb-eddfc7a690bd&pd_rd_i=9365697948&psc=1',
        'https://www.amazon.in/dp/9365698030?ref_=ppx_hzod_title_dt_b_fed_asin_title_3_0',
        'https://www.amazon.in/dp/9389178118?ref_=ppx_hzod_title_dt_b_fed_asin_title_2_6',
    ]
    
    # If URLs provided as command line arguments, use those instead
    if len(sys.argv) > 1:
        urls = sys.argv[1:]
    
    results = []
    
    for url in urls:
        result = scrape_amazon_product(url)
        results.append(result)
        
        # Print results
        print("\n" + "="*80)
        print(f"URL: {result.get('url', 'N/A')}")
        print(f"ASIN: {result.get('asin', 'N/A')}")
        print(f"Title: {result.get('title', 'N/A')}")
        print(f"Price: {result.get('price', 'N/A')}")
        if result.get('compare_at_price'):
            print(f"Compare At Price: {result.get('compare_at_price')}")
        print(f"Description: {result.get('description', 'N/A')[:200]}..." if result.get('description') else "Description: N/A")
        print(f"Number of Images: {len(result.get('images', []))}")
        if result.get('images'):
            print("Images:")
            for i, img_url in enumerate(result.get('images', [])[:5], 1):  # Show first 5
                print(f"  {i}. {img_url}")
            if len(result.get('images', [])) > 5:
                print(f"  ... and {len(result.get('images', [])) - 5} more")
        if result.get('error'):
            print(f"Error: {result.get('error')}")
        print("="*80 + "\n")
    
    # Save results to JSON file
    output_file = 'amazon_scrape_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to {output_file}")


if __name__ == '__main__':
    main()

