#!/usr/bin/env python3
"""
Hello Friend Books Product Scraper
Extracts title, description, price, and all images from Hello Friend Books product pages.
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
    """Extract product slug from Hello Friend Books URL."""
    # URLs like: https://hellofriendbooks.com/product/hello-friend-books-jungle-animals-puzzle-book-board-book-with-jigsaw-puzzles-for-kids/
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
    
    # Method 2: Look for meta og:title
    og_title = soup.find('meta', property='og:title')
    if og_title:
        title = og_title.get('content', '').strip()
        if title:
            return title
    
    # Method 3: Extract from title tag
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text(strip=True)
        # Remove trailing " - Hello Friend Books" or similar
        title = re.sub(r'\s*-\s*Hello Friend Books.*$', '', title, flags=re.IGNORECASE)
        if title:
            return title
    
    return None


def extract_price(soup, content):
    """Extract product price from the page."""
    price = None
    compare_at_price = None
    
    # Method 1: Look for woocommerce price elements
    price_selectors = [
        '.price .amount',
        '.woocommerce-Price-amount',
        '.price',
        '[class*="price"]',
    ]
    for selector in price_selectors:
        price_elems = soup.select(selector)
        for elem in price_elems:
            text = elem.get_text(strip=True)
            # Extract price number (look for ₹ or numbers)
            match = re.search(r'₹?\s*(\d+\.?\d*)', text.replace(',', ''))
            if match:
                try:
                    price_value = float(match.group(1))
                    if price_value > 0:
                        price = f"{price_value:.2f}"
                        break
                except:
                    pass
        if price:
            break
    
    return {
        'price': price,
        'compare_at_price': compare_at_price,
    }


def extract_description(soup):
    """Extract product description from the page."""
    description_parts = []
    
    # Method 1: Look for description in tab-description div
    desc_tab = soup.find('div', id='tab-description')
    if desc_tab:
        paragraphs = desc_tab.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text and len(text) > 20:
                description_parts.append(text)
    
    # Method 2: Look for description in any div with class containing 'description'
    if not description_parts:
        desc_divs = soup.find_all('div', class_=lambda x: x and 'description' in str(x).lower())
        for div in desc_divs:
            paragraphs = div.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 20 and text not in description_parts:
                    description_parts.append(text)
    
    # Method 3: Look for meta description (last resort)
    if not description_parts:
        meta_desc = soup.find('meta', property='og:description')
        if meta_desc:
            desc = meta_desc.get('content', '').strip()
            if desc and len(desc) > 20:
                description_parts.append(desc)
    
    if description_parts:
        return '\n\n'.join(description_parts)
    
    return None


def extract_images(soup, content):
    """Extract product images from the page."""
    images = []
    image_urls = set()
    
    # Method 1: Look for images with data-large_image attribute (woocommerce product gallery)
    large_imgs = soup.find_all('img', attrs={'data-large_image': True})
    for img in large_imgs:
        img_url = img.get('data-large_image', '').strip()
        if img_url and img_url.startswith('http') and img_url not in image_urls:
            images.append(img_url)
            image_urls.add(img_url)
    
    # Method 2: Look for images in woocommerce-product-gallery
    gallery = soup.find('div', class_=lambda x: x and 'woocommerce-product-gallery' in str(x).lower())
    if gallery:
        gallery_imgs = gallery.find_all('img')
        for img in gallery_imgs:
            # Prefer data-large_image (full size), then data-src, then src
            img_url = (img.get('data-large_image') or 
                      img.get('data-src') or 
                      img.get('src', '')).strip()
            if img_url:
                # Make sure it's a full URL
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = 'https://hellofriendbooks.com' + img_url
                
                if img_url.startswith('http') and img_url not in image_urls:
                    # Filter out resized thumbnails (look for -150x, -400x, -700x, -1140x, etc. in URL)
                    # Only keep original full-size images
                    if not re.search(r'-\d+x\d+\.(?:png|jpg|jpeg)', img_url):
                        images.append(img_url)
                        image_urls.add(img_url)
    
    # Method 3: Look for og:image meta tag (only if not already found)
    if not images:
        og_image = soup.find('meta', property='og:image')
        if og_image:
            img_url = og_image.get('content', '').strip()
            # Filter out resized versions
            if img_url and not re.search(r'-\d+x\d+\.(?:png|jpg|jpeg)', img_url):
                if img_url not in image_urls:
                    images.append(img_url)
                    image_urls.add(img_url)
    
    # Filter out any resized images that might have slipped through
    final_images = []
    for img_url in images:
        # Skip resized images (contain -WIDTHxHEIGHT before extension)
        if not re.search(r'-\d+x\d+\.(?:png|jpg|jpeg)', img_url):
            final_images.append(img_url)
    
    # Deduplicate and return
    return list(dict.fromkeys(final_images))  # Preserves order while removing duplicates


def scrape_hellofriendbooks_product(url):
    """Scrape product information from a Hello Friend Books URL."""
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
        'https://hellofriendbooks.com/product/hello-friend-books-my-shaped-story-book-ugly-ducking-shaped-story-board-book-for-kids/',
    ]
    
    # If URLs provided as command line arguments, use those instead
    if len(sys.argv) > 1:
        urls = sys.argv[1:]
    
    results = []
    
    for url in urls:
        result = scrape_hellofriendbooks_product(url)
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
    output_file = 'hellofriendbooks_scrape_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to {output_file}")


if __name__ == '__main__':
    main()
