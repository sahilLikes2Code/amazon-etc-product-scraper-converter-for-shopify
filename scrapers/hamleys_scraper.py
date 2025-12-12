#!/usr/bin/env python3
"""
Hamleys Product Scraper
Extracts title, description, price, and all images from Hamleys product pages.
"""

import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import sys


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


def extract_product_id(url):
    """Extract product ID from Hamleys URL."""
    # URLs like: https://hamleys.in/product/product-name-12345678
    match = re.search(r'/product/[^/]+-(\d+)$', url)
    if match:
        return match.group(1)
    return None


def extract_title(soup, content):
    """Extract product title from the page."""
    # Method 1: Look for h1
    h1 = soup.find('h1')
    if h1:
        title = h1.get_text(strip=True)
        if title and len(title) > 5:
            return title
    
    # Method 2: Look for meta og:title
    og_title = soup.find('meta', property='og:title')
    if og_title:
        title = og_title.get('content', '').strip()
        if title:
            return title
    
    # Method 3: Look for JSON-LD structured data
    json_ld = soup.find('script', type='application/ld+json')
    if json_ld and json_ld.string:
        try:
            data = json.loads(json_ld.string)
            if isinstance(data, dict) and 'name' in data:
                return data['name']
            if isinstance(data, list) and len(data) > 0 and 'name' in data[0]:
                return data[0]['name']
        except:
            pass
    
    # Method 4: Look for title in script tags with product data
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and 'product' in script.string.lower():
            # Try to find name or title in JSON
            name_match = re.search(r'"name"\s*:\s*"([^"]+)"', script.string)
            if name_match:
                return name_match.group(1)
            title_match = re.search(r'"title"\s*:\s*"([^"]+)"', script.string)
            if title_match:
                return title_match.group(1)
    
    # Method 5: Extract from URL (fallback)
    parsed = urlparse(content.split('\n')[0] if '\n' in content else '')
    path = parsed.path
    if '/product/' in path:
        # Extract product name from URL
        product_part = path.split('/product/')[-1]
        # Remove the ID at the end
        product_name = re.sub(r'-\d+$', '', product_part)
        # Replace hyphens with spaces and title case
        if product_name:
            return product_name.replace('-', ' ').title()
    
    return None


def extract_price(soup, content):
    """Extract product price from the page."""
    price = None
    compare_at_price = None
    
    # Method 1: Look for JSON-LD structured data
    json_ld = soup.find_all('script', type='application/ld+json')
    for script in json_ld:
        if script.string:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    if 'offers' in data:
                        offers = data['offers']
                        if isinstance(offers, dict):
                            if 'price' in offers:
                                price_value = offers.get('price', '')
                                if price_value:
                                    # Extract numeric value
                                    match = re.search(r'(\d+\.?\d*)', str(price_value))
                                    if match:
                                        price = f"{float(match.group(1)):.2f}"
                            # Check for priceSpecification for compare at price
                            if 'priceSpecification' in offers:
                                spec = offers['priceSpecification']
                                if isinstance(spec, dict):
                                    if 'maxPrice' in spec:
                                        max_price = spec.get('maxPrice', '')
                                        if max_price:
                                            match = re.search(r'(\d+\.?\d*)', str(max_price))
                                            if match:
                                                compare_at_price = f"{float(match.group(1)):.2f}"
                        elif isinstance(offers, list) and len(offers) > 0:
                            # Take first offer
                            offer = offers[0]
                            if 'price' in offer:
                                price_value = offer.get('price', '')
                                if price_value:
                                    match = re.search(r'(\d+\.?\d*)', str(price_value))
                                    if match:
                                        price = f"{float(match.group(1)):.2f}"
                if isinstance(data, list):
                    for item in data:
                        if 'offers' in item:
                            offers = item['offers']
                            if isinstance(offers, dict) and 'price' in offers:
                                price_value = offers['price']
                                match = re.search(r'(\d+\.?\d*)', str(price_value))
                                if match:
                                    price = f"{float(match.group(1)):.2f}"
            except:
                pass
    
    # Method 2: Look for price in meta tags
    price_meta = soup.find('meta', property='product:price:amount')
    if price_meta:
        price_value = price_meta.get('content', '')
        if price_value:
            try:
                price = f"{float(price_value):.2f}"
            except:
                pass
    
    # Method 3: Look for price in script tags (try to parse JSON)
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string:
            # Try to find min_price_effective (Hamleys uses this)
            min_price_match = re.search(r'"min_price_effective"\s*:\s*(\d+)', script.string)
            if min_price_match:
                try:
                    price_val = float(min_price_match.group(1))
                    if price_val > 0:
                        price = f"{price_val:.2f}"
                except:
                    pass
            
            # Try to find and parse JSON with price data
            try:
                # Look for JSON objects that might contain price
                json_matches = re.findall(r'\{[^{}]*"price"[^{}]*\}', script.string, re.DOTALL)
                for json_str in json_matches:
                    try:
                        data = json.loads(json_str)
                        if 'price' in data:
                            price_val = data['price']
                            if isinstance(price_val, (int, float)) and price_val > 0:
                                if not price:
                                    price = f"{float(price_val):.2f}"
                    except:
                        pass
                
                # Also try to find amount in JSON
                json_matches = re.findall(r'\{[^{}]*"amount"[^{}]*\}', script.string, re.DOTALL)
                for json_str in json_matches:
                    try:
                        data = json.loads(json_str)
                        if 'amount' in data:
                            amount_val = data['amount']
                            if isinstance(amount_val, (int, float)) and amount_val > 0:
                                if not price:
                                    price = f"{float(amount_val):.2f}"
                    except:
                        pass
            except:
                pass
            
            # Look for price patterns (fallback)
            price_patterns = [
                r'"price"\s*:\s*"?(\d+\.?\d*)"?',
                r'"amount"\s*:\s*"?(\d+\.?\d*)"?',
                r'price["\']?\s*[:=]\s*["\']?(\d+\.?\d*)',
            ]
            for pattern in price_patterns:
                matches = re.findall(pattern, script.string)
                for match in matches:
                    try:
                        price_val = float(match)
                        if price_val > 0:
                            if not price:
                                price = f"{price_val:.2f}"
                            elif price_val > float(price):
                                compare_at_price = price
                                price = f"{price_val:.2f}"
                    except:
                        pass
    
    # Method 4: Look for price in HTML elements
    price_selectors = [
        '.price',
        '[class*="price"]',
        '[class*="Price"]',
        '[data-price]',
    ]
    for selector in price_selectors:
        elements = soup.select(selector)
        for elem in elements:
            text = elem.get_text(strip=True)
            # Extract price from text (look for ₹ or numbers)
            match = re.search(r'₹?\s*(\d+[,\d]*\.?\d*)', text.replace(',', ''))
            if match:
                try:
                    price_val = float(match.group(1))
                    if price_val > 0:
                        if not price:
                            price = f"{price_val:.2f}"
                except:
                    pass
    
    return {
        'price': price,
        'compare_at_price': compare_at_price,
    }


def extract_description(soup):
    """Extract product description from the page."""
    description_parts = []
    
    # Method 1: Look for JSON-LD structured data
    json_ld = soup.find_all('script', type='application/ld+json')
    for script in json_ld:
        if script.string:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'description' in data:
                    desc = data['description']
                    if desc and len(desc) > 10:
                        description_parts.append(desc)
                if isinstance(data, list):
                    for item in data:
                        if 'description' in item:
                            desc = item['description']
                            if desc and len(desc) > 10:
                                description_parts.append(desc)
            except:
                pass
    
    # Method 2: Look for meta description
    meta_desc = soup.find('meta', property='og:description')
    if meta_desc:
        desc = meta_desc.get('content', '').strip()
        if desc and len(desc) > 10:
            description_parts.append(desc)
    
    # Method 3: Look for description in HTML
    desc_selectors = [
        '[class*="description"]',
        '[class*="Description"]',
        '[id*="description"]',
        '[id*="Description"]',
        '.product-description',
        '.productDescription',
    ]
    
    for selector in desc_selectors:
        elements = soup.select(selector)
        for element in elements:
            text = element.get_text(strip=True)
            if text and len(text) > 20:
                # Filter out navigation and UI text
                if not any(skip in text.lower() for skip in [
                    'cookie', 'privacy', 'terms', 'menu', 'navigation',
                    'skip to', 'click here', 'read more'
                ]):
                    if text not in description_parts:
                        description_parts.append(text)
    
    # Method 4: Look for description in script tags
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and 'description' in script.string.lower():
            desc_match = re.search(r'"description"\s*:\s*"([^"]+)"', script.string)
            if desc_match:
                desc = desc_match.group(1)
                if desc and len(desc) > 10 and desc not in description_parts:
                    description_parts.append(desc)
    
    if description_parts:
        return '\n\n'.join(description_parts)
    
    return None


def extract_images(soup, content):
    """Extract product images from the page."""
    images = []
    image_urls = set()
    
    # Method 1: Look for JSON-LD structured data
    json_ld = soup.find_all('script', type='application/ld+json')
    for script in json_ld:
        if script.string:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    if 'image' in data:
                        img = data['image']
                        if isinstance(img, str) and img:
                            if img not in image_urls:
                                images.append(img)
                                image_urls.add(img)
                        elif isinstance(img, list):
                            for img_url in img:
                                if isinstance(img_url, str) and img_url and img_url not in image_urls:
                                    images.append(img_url)
                                    image_urls.add(img_url)
                if isinstance(data, list):
                    for item in data:
                        if 'image' in item:
                            img = item['image']
                            if isinstance(img, str) and img and img not in image_urls:
                                images.append(img)
                                image_urls.add(img)
                            elif isinstance(img, list):
                                for img_url in img:
                                    if isinstance(img_url, str) and img_url and img_url not in image_urls:
                                        images.append(img_url)
                                        image_urls.add(img_url)
            except:
                pass
    
    # Method 2: Look for og:image meta tag
    og_image = soup.find('meta', property='og:image')
    if og_image:
        img_url = og_image.get('content', '').strip()
        if img_url and img_url not in image_urls:
            images.append(img_url)
            image_urls.add(img_url)
    
    # Method 3: Search raw content for image URLs in JSON format
    # Images are in JSON with unicode escapes: "url":"https://cdn.fynd.com...pictures/item...original...jpeg"
    # Match the JSON pattern with unicode escapes
    url_pattern = r'"url"\s*:\s*"https[^"]*cdn\.fynd\.com[^"]*pictures[^"]*item[^"]*original[^"]*\.(?:jpeg|jpg|png|webp)"'
    url_matches = re.findall(url_pattern, content, re.IGNORECASE)
    for match in url_matches:
        # Decode unicode escapes
        decoded = match.replace('\\u002F', '/').replace('\\u002f', '/')
        # Extract URL from the match
        url_match = re.search(r'https://cdn\.fynd\.com[^"]+', decoded)
        if url_match:
            img_url = url_match.group(0)
            # Clean up: remove query params
            img_url = img_url.split('?')[0]
            # Ensure it has /original/ and ends with image extension
            if '/original/' in img_url and img_url.endswith(('.jpeg', '.jpg', '.png', '.webp')):
                if img_url not in image_urls:
                    if not any(skip in img_url.lower() for skip in ['icon', 'logo', 'navigation', 'theme', 'favicon', 'brand']):
                        images.append(img_url)
                        image_urls.add(img_url)
    
    # Also try patterns without unicode escapes (for decoded content)
    decoded_content = content.replace('\\u002F', '/').replace('\\u002f', '/')
    fynd_patterns = [
        r'https://cdn\.fynd\.com[^"\\s<>]*/products/pictures/item/[^"\\s<>]*/original/[^"\\s<>]+\.(?:jpeg|jpg|png|webp)',
        r'https://cdn\.fynd\.com[^"\\s<>]*/pictures/item/[^"\\s<>]*/original/[^"\\s<>]+\.(?:jpeg|jpg|png|webp)',
    ]
    for pattern in fynd_patterns:
        fynd_matches = re.findall(pattern, decoded_content, re.IGNORECASE)
        for match in fynd_matches:
            img_url = match.split('?')[0].split('"')[0].split("'")[0]
            if img_url.startswith('http') and img_url not in image_urls:
                if '/original/' in img_url:
                    if not any(skip in img_url.lower() for skip in ['icon', 'logo', 'navigation', 'theme', 'favicon', 'brand']):
                        images.append(img_url)
                        image_urls.add(img_url)
    
    # Method 4: Look for images in script tags
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and 'cdn.fynd.com' in script.string:
            # Look for URLs in the script content
            script_urls = re.findall(r'https://cdn\.fynd\.com[^"\\s]+', script.string)
            for url in script_urls:
                # Clean up
                url = url.replace('\\/', '/').replace('\\u002F', '/')
                if '\\u' in url:
                    try:
                        url = url.encode().decode('unicode_escape')
                    except:
                        pass
                # Only product images
                if url.startswith('http') and url not in image_urls:
                    if ('/pictures/item/' in url or '/products/' in url) and url.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                        if not any(skip in url.lower() for skip in ['icon', 'logo', 'navigation', 'theme', 'favicon']):
                            images.append(url)
                            image_urls.add(url)
    
    # Method 5: Look for product images in HTML img tags (with srcset)
    # Hamleys uses img tags with srcset containing multiple sizes
    # We want the original size (with /original/ in path)
    img_tags = soup.find_all('img')
    for img in img_tags:
        # Check src attribute first (usually has the original)
        img_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
        
        # Also check srcset for original size
        srcset = img.get('srcset', '')
        if srcset and '/original/' in srcset:
            # Extract URL with /original/ from srcset
            original_match = re.search(r'(https://cdn\.fynd\.com[^\s]+/original/[^\s]+)', srcset)
            if original_match:
                img_url = original_match.group(1).split('?')[0]  # Remove query params for cleaner URL
        
        if img_url and 'cdn.fynd.com' in img_url:
            # Make sure it's a full URL
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            elif img_url.startswith('/'):
                img_url = 'https://hamleys.in' + img_url
            
            # Clean up query parameters - prefer original size
            if '/original/' in img_url:
                # Remove query params to get clean URL
                img_url = img_url.split('?')[0]
            elif '/resize-' in img_url:
                # Skip resized versions, we want original
                continue
            
            if img_url.startswith('http') and img_url not in image_urls:
                # Only product images, not icons/logos
                if '/pictures/item/' in img_url or '/products/' in img_url:
                    if not any(skip in img_url.lower() for skip in ['icon', 'logo', 'navigation', 'theme', 'favicon', 'brand']):
                        # Prefer original size
                        if '/original/' in img_url:
                            images.append(img_url)
                            image_urls.add(img_url)
                        elif '/resize-' not in img_url:
                            # Fallback to non-resized if no original found
                            images.append(img_url)
                            image_urls.add(img_url)
    
    # Sort images to put originals first, then deduplicate
    # Remove resized versions if we have originals
    final_images = []
    seen_base = set()
    for img_url in images:
        # Extract base image identifier (without resize info)
        base_match = re.search(r'/([^/]+\.(?:jpeg|jpg|png|webp))', img_url)
        if base_match:
            base_id = base_match.group(1)
            if '/original/' in img_url:
                # Original - add and mark base as seen
                if base_id not in seen_base:
                    final_images.append(img_url)
                    seen_base.add(base_id)
            elif base_id not in seen_base:
                # Not original but no original found yet
                final_images.append(img_url)
                seen_base.add(base_id)
        else:
            # No base match, add as is
            if img_url not in final_images:
                final_images.append(img_url)
    
    return final_images
    
    # Deduplicate and return
    return list(dict.fromkeys(images))  # Preserves order while removing duplicates


def scrape_hamleys_product(url):
    """Scrape product information from a Hamleys URL."""
    print(f"Scraping: {url}")
    
    try:
        response = requests.get(url, headers=get_headers(), timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        content = response.text
        
        price_info = extract_price(soup, content)
        
        result = {
            'url': url,
            'product_id': extract_product_id(url),
            'title': extract_title(soup, content),
            'description': extract_description(soup),
            'price': price_info.get('price'),
            'compare_at_price': price_info.get('compare_at_price'),
            'images': extract_images(soup, content),
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
        'https://hamleys.in/product/simba-masha-and-her-animal-friends-multicolour-3y-17032828',
    ]
    
    # If URLs provided as command line arguments, use those instead
    if len(sys.argv) > 1:
        urls = sys.argv[1:]
    
    results = []
    
    for url in urls:
        result = scrape_hamleys_product(url)
        results.append(result)
        
        # Print results
        print("\n" + "="*80)
        print(f"URL: {result.get('url', 'N/A')}")
        print(f"Product ID: {result.get('product_id', 'N/A')}")
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
    output_file = 'hamleys_scrape_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to {output_file}")


if __name__ == '__main__':
    main()

