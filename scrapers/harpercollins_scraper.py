#!/usr/bin/env python3
"""
HarperCollins Product Scraper
Extracts title, description, price, and all images from HarperCollins product pages.
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


def extract_product_slug(url):
    """Extract product slug from HarperCollins URL."""
    # URLs like: https://harpercollins.co.in/product/my-emotions/
    match = re.search(r'/product/([^/]+)/?$', url)
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
    
    # Method 2: Look for JSON-LD mainEntity.name
    json_lds = soup.find_all('script', type='application/ld+json')
    for json_ld in json_lds:
        if json_ld.string:
            try:
                # Try to parse JSON, handle trailing commas
                json_str = json_ld.string.strip()
                # Remove trailing commas before closing braces/brackets
                json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                data = json.loads(json_str)
                if isinstance(data, dict) and 'mainEntity' in data:
                    book = data['mainEntity']
                    if isinstance(book, dict) and 'name' in book:
                        title = book['name']
                        # Decode HTML entities
                        title = title.replace('&#8211;', '-').replace('&amp;', '&')
                        if title:
                            return title
            except:
                pass
    
    # Method 3: Look for meta og:title
    og_title = soup.find('meta', property='og:title')
    if og_title:
        title = og_title.get('content', '').strip()
        if title:
            return title
    
    # Method 4: Extract from title tag
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text(strip=True)
        # Remove trailing " | BOOKTOPUS" or similar
        title = re.sub(r'\s*\|\s*.*$', '', title)
        if title:
            return title
    
    return None


def extract_price(soup, content):
    """Extract product price from the page."""
    price = None
    compare_at_price = None
    
    # Method 1: Look for JSON-LD mainEntity.offers.price
    json_lds = soup.find_all('script', type='application/ld+json')
    for json_ld in json_lds:
        if json_ld.string:
            try:
                json_str = json_ld.string.strip()
                # Remove trailing commas
                json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                data = json.loads(json_str)
                if isinstance(data, dict) and 'mainEntity' in data:
                    book = data['mainEntity']
                    if isinstance(book, dict) and 'offers' in book:
                        offers = book['offers']
                        if isinstance(offers, dict) and 'price' in offers:
                            price_value = offers['price']
                            try:
                                price = f"{float(price_value):.2f}"
                            except:
                                pass
                        elif isinstance(offers, list) and len(offers) > 0:
                            if 'price' in offers[0]:
                                price_value = offers[0]['price']
                                try:
                                    price = f"{float(price_value):.2f}"
                                except:
                                    pass
            except:
                pass
    
    # Method 2: Look for price in HTML elements
    price_selectors = [
        '.price',
        '.woocommerce-Price-amount',
        '[class*="price"]',
    ]
    for selector in price_selectors:
        price_elem = soup.select_one(selector)
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            # Extract price number (look for ₹ or numbers)
            match = re.search(r'₹?\s*(\d+\.?\d*)', price_text.replace(',', ''))
            if match:
                try:
                    price_value = float(match.group(1))
                    if price_value > 0:
                        price = f"{price_value:.2f}"
                        break
                except:
                    pass
    
    return {
        'price': price,
        'compare_at_price': compare_at_price,
    }


def extract_description(soup):
    """Extract product description from the page."""
    description_parts = []
    
    # Method 1: Look for "About the book" h3 heading and extract content after it
    about_heading = soup.find('h3', string=lambda text: text and 'About the book' in text)
    if about_heading:
        # Find the parent container (usually book-desc or similar)
        parent = about_heading.find_parent()
        if parent:
            # Get all content after the h3 heading
            # Find all siblings after the h3
            current = about_heading.find_next_sibling()
            while current:
                # Stop if we hit another major section (h2, h3, h4, or div with class containing 'author', 'tags', 'other-info')
                if current.name in ['h2', 'h3', 'h4']:
                    break
                if current.name == 'div' and current.get('class'):
                    classes = ' '.join(current.get('class', []))
                    if any(keyword in classes.lower() for keyword in ['author', 'tags', 'other-info', 'book-tags', 'books-slider']):
                        break
                
                # Extract paragraphs
                if current.name == 'p':
                    text = current.get_text(strip=True)
                    if text and len(text) > 10:
                        description_parts.append(text)
                # Extract list items
                elif current.name == 'ul':
                    list_items = current.find_all('li')
                    for li in list_items:
                        text = li.get_text(strip=True)
                        if text and len(text) > 5:
                            description_parts.append(text)
                # If it's a div, check for paragraphs and lists inside
                elif current.name == 'div':
                    paragraphs = current.find_all('p', recursive=False)
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if text and len(text) > 10:
                            description_parts.append(text)
                    list_items = current.find_all('li', recursive=False)
                    for li in list_items:
                        text = li.get_text(strip=True)
                        if text and len(text) > 5:
                            description_parts.append(text)
                
                current = current.find_next_sibling()
    
    # Method 2: Look for JSON-LD mainEntity.description (fallback, but prefer "About the book")
    if not description_parts:
        json_lds = soup.find_all('script', type='application/ld+json')
        for json_ld in json_lds:
            if json_ld.string:
                try:
                    json_str = json_ld.string.strip()
                    # Remove trailing commas
                    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                    data = json.loads(json_str)
                    if isinstance(data, dict) and 'mainEntity' in data:
                        book = data['mainEntity']
                        if isinstance(book, dict) and 'description' in book:
                            desc_html = book['description']
                            if desc_html:
                                # Parse HTML description
                                desc_soup = BeautifulSoup(desc_html, 'html.parser')
                                # Get paragraphs
                                paragraphs = desc_soup.find_all('p')
                                for p in paragraphs:
                                    text = p.get_text(strip=True)
                                    if text and len(text) > 10:
                                        description_parts.append(text)
                                # Get list items
                                list_items = desc_soup.find_all('li')
                                for li in list_items:
                                    text = li.get_text(strip=True)
                                    if text and len(text) > 5:
                                        description_parts.append(text)
                except:
                    pass
    
    # Method 3: Look for meta description (last resort)
    if not description_parts:
        meta_desc = soup.find('meta', property='og:description')
        if meta_desc:
            desc = meta_desc.get('content', '').strip()
            if desc and len(desc) > 20:
                # Clean up the description
                desc = re.sub(r'\s+', ' ', desc)
                description_parts.append(desc)
    
    if description_parts:
        return '\n\n'.join(description_parts)
    
    return None


def extract_isbn(soup):
    """Extract ISBN from the page."""
    json_lds = soup.find_all('script', type='application/ld+json')
    for json_ld in json_lds:
        if json_ld.string:
            try:
                json_str = json_ld.string.strip()
                json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                data = json.loads(json_str)
                if isinstance(data, dict) and 'mainEntity' in data:
                    book = data['mainEntity']
                    if isinstance(book, dict) and 'isbn' in book:
                        return book['isbn']
            except:
                pass
    return None


def extract_images(soup, content):
    """Extract product images from the page."""
    images = []
    image_urls = set()
    
    # Get ISBN to filter images
    isbn = extract_isbn(soup)
    
    # Method 1: Look for JSON-LD mainEntity.image
    json_lds = soup.find_all('script', type='application/ld+json')
    for json_ld in json_lds:
        if json_ld.string:
            try:
                json_str = json_ld.string.strip()
                # Remove trailing commas
                json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                data = json.loads(json_str)
                if isinstance(data, dict) and 'mainEntity' in data:
                    book = data['mainEntity']
                    if isinstance(book, dict) and 'image' in book:
                        img_url = book['image']
                        if isinstance(img_url, str) and img_url.startswith('http'):
                            if img_url not in image_urls:
                                images.append(img_url)
                                image_urls.add(img_url)
            except:
                pass
    
    # Method 2: Look for book cover images matching the ISBN (strict filtering)
    if isbn:
        # Pattern: https://harpercollins.co.in/book-cover/.../ISBN.jpg
        # Only match URLs that end with /ISBN.jpg (not other ISBNs)
        img_pattern = rf'https://[^"\s<>]*harpercollins\.co\.in[^"\s<>]*book-cover[^"\s<>]*/{isbn}\.(?:jpg|jpeg|png)'
        img_matches = re.findall(img_pattern, content, re.IGNORECASE)
        for match in img_matches:
            # Double-check the ISBN is in the URL
            if isbn in match and match not in image_urls:
                images.append(match)
                image_urls.add(match)
    else:
        # Fallback: get first book cover image found (but warn)
        img_pattern = r'https://[^"\s<>]*harpercollins\.co\.in[^"\s<>]*book-cover[^"\s<>]*\.(?:jpg|jpeg|png)'
        img_matches = re.findall(img_pattern, content, re.IGNORECASE)
        # Only take the first one if no ISBN
        if img_matches and img_matches[0] not in image_urls:
            images.append(img_matches[0])
            image_urls.add(img_matches[0])
    
    # Method 3: Look for images in img tags (strictly filter by ISBN if available)
    img_tags = soup.find_all('img')
    for img in img_tags:
        src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
        if src and 'book-cover' in src:
            # Strictly filter by ISBN if available - must contain the ISBN
            if isbn:
                if isbn not in src:
                    continue  # Skip images that don't match the ISBN
            
            # Make sure it's a full URL
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = 'https://harpercollins.co.in' + src
            
            if src.startswith('http') and src not in image_urls:
                images.append(src)
                image_urls.add(src)
    
    # Method 4: Look for og:image meta tag (only if matches ISBN)
    og_image = soup.find('meta', property='og:image')
    if og_image:
        img_url = og_image.get('content', '').strip()
        # Only add if it's a book cover and matches ISBN (or no ISBN filter)
        if img_url and 'book-cover' in img_url:
            if not isbn or isbn in img_url:
                if img_url not in image_urls:
                    images.append(img_url)
                    image_urls.add(img_url)
    
    # Deduplicate: normalize www vs non-www URLs and remove exact duplicates
    normalized_images = []
    seen_normalized = set()
    for img_url in images:
        # Normalize: remove www. prefix for comparison
        normalized = img_url.replace('www.harpercollins.co.in', 'harpercollins.co.in')
        if normalized not in seen_normalized:
            normalized_images.append(img_url)  # Keep original URL
            seen_normalized.add(normalized)
    
    # Prefer non-www URLs, but keep www if that's the only version
    final_images = []
    for img_url in normalized_images:
        normalized = img_url.replace('www.harpercollins.co.in', 'harpercollins.co.in')
        # If we already have the non-www version, skip www version
        if 'www.harpercollins.co.in' in img_url:
            non_www = img_url.replace('www.harpercollins.co.in', 'harpercollins.co.in')
            if non_www not in [u.replace('www.harpercollins.co.in', 'harpercollins.co.in') for u in final_images]:
                final_images.append(img_url)
        else:
            final_images.append(img_url)
    
    return final_images


def scrape_harpercollins_product(url):
    """Scrape product information from a HarperCollins URL."""
    print(f"Scraping: {url}")
    
    try:
        response = requests.get(url, headers=get_headers(), timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        content = response.text
        
        price_info = extract_price(soup, content)
        
        result = {
            'url': url,
            'product_slug': extract_product_slug(url),
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
        'https://harpercollins.co.in/product/my-emotions/',
    ]
    
    # If URLs provided as command line arguments, use those instead
    if len(sys.argv) > 1:
        urls = sys.argv[1:]
    
    results = []
    
    for url in urls:
        result = scrape_harpercollins_product(url)
        results.append(result)
        
        # Print results
        print("\n" + "="*80)
        print(f"URL: {result.get('url', 'N/A')}")
        print(f"Product Slug: {result.get('product_slug', 'N/A')}")
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
    output_file = 'harpercollins_scrape_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to {output_file}")


if __name__ == '__main__':
    main()
