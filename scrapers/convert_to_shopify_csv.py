#!/usr/bin/env python3
"""
Convert Amazon scraped data to Shopify CSV format
"""

import json
import csv
import re
from urllib.parse import quote


def create_handle(title):
    """Create a URL-friendly handle from title."""
    # Convert to lowercase
    handle = title.lower()
    # Replace spaces and special chars with hyphens
    handle = re.sub(r'[^\w\s-]', '', handle)
    handle = re.sub(r'[-\s]+', '-', handle)
    # Remove leading/trailing hyphens
    handle = handle.strip('-')
    # Limit length
    if len(handle) > 255:
        handle = handle[:255]
    return handle


def description_to_html(description):
    """Convert plain text description to HTML format."""
    if not description:
        return ""
    
    # Split by double newlines to create paragraphs
    paragraphs = description.split('\n\n')
    html_parts = []
    list_items = []
    in_list = False
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # Check if it's a bullet point (starts with common bullet indicators or action verbs)
        # But exclude phrases that end with colon (like "This discovery book:")
        is_bullet = (
            (para.startswith('- ') or para.startswith('• ') or para.startswith('* ')) or
            (not para.endswith(':') and any(para.startswith(x) for x in [
                'Makes ', 'Turns ', 'Encourages ', 'Includes ', 'Perfect ', 
                'Stories ', 'Develops ', 'Builds ', 'Gorgeous ', 'Features '
            ])) or
            (len(para) < 100 and not para.endswith('.') and not para.endswith(':'))  # Short lines without periods/colons are likely bullets
        )
        
        if is_bullet:
            # It's a bullet point
            text = para.lstrip('- •*').strip()
            list_items.append(f'<li>{text}</li>')
            in_list = True
        else:
            # If we were building a list, close it first
            if in_list and list_items:
                html_parts.append('<ul>')
                html_parts.extend(list_items)
                html_parts.append('</ul>')
                list_items = []
                in_list = False
            # Regular paragraph
            html_parts.append(f'<p>{para}</p>')
    
    # Close any remaining list
    if in_list and list_items:
        html_parts.append('<ul>')
        html_parts.extend(list_items)
        html_parts.append('</ul>')
    
    return '\n'.join(html_parts) if html_parts else f'<p>{description}</p>'


def convert_to_shopify_csv(json_file, output_file, default_price='0.00', default_type='Book', default_vendor=''):
    """Convert Amazon scrape results to Shopify CSV format."""
    
    # Read JSON data
    with open(json_file, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    # Shopify CSV headers (only necessary fields)
    headers = [
        'Handle',
        'Title',
        'Body (HTML)',
        'Vendor',
        'Type',
        'Tags',
        'Published',
        'Option1 Name',
        'Option1 Value',
        'Variant Grams',
        'Variant Inventory Qty',
        'Variant Inventory Policy',
        'Variant Fulfillment Service',
        'Variant Price',
        'Variant Compare At Price',
        'Variant Requires Shipping',
        'Variant Taxable',
        'Image Src',
        'Image Position',
        'Image Alt Text',
        'Status',
    ]
    
    rows = []
    
    for product in products:
        if 'error' in product:
            print(f"Skipping product with error: {product.get('url', 'Unknown')}")
            continue
        
        title = product.get('title', '')
        if not title:
            print(f"Skipping product without title: {product.get('url', 'Unknown')}")
            continue
        
        handle = create_handle(title)
        description = product.get('description', '')
        description_html = description_to_html(description)
        images = product.get('images', [])
        asin = product.get('asin', '')
        price = product.get('price') or default_price
        compare_at_price = product.get('compare_at_price') or ''
        
        # Get category and tags from product data (if available from CSV)
        product_category = product.get('category', '')
        product_type = product_category if product_category else default_type
        
        # Use tags from CSV if available, otherwise generate from title
        tags_from_csv = product.get('tags', '')
        if tags_from_csv:
            tags_str = tags_from_csv
        else:
            # Fallback: Create tags from title (extract key words)
            tags = []
            if 'book' in title.lower():
                tags.append('Book')
            if 'torch' in title.lower():
                tags.append('Torch')
            if 'discovery' in title.lower():
                tags.append('Discovery')
            if 'interactive' in title.lower():
                tags.append('Interactive')
            if 'kids' in title.lower() or 'children' in title.lower():
                tags.append('Kids')
            tags_str = ', '.join(tags) if tags else ''
        
        
        # If no images, create one row
        if not images:
            row = {
                'Handle': handle,
                'Title': title,
                'Body (HTML)': description_html,
                'Vendor': default_vendor,
                'Type': product_type,
                'Tags': tags_str,
                'Published': 'TRUE',
                'Option1 Name': '',
                'Option1 Value': '',
                'Variant Grams': '',
                'Variant Inventory Qty': '',
                'Variant Inventory Policy': 'deny',
                'Variant Fulfillment Service': 'manual',
                'Variant Price': price,
                'Variant Compare At Price': compare_at_price,
                'Variant Requires Shipping': 'TRUE',
                'Variant Taxable': 'TRUE',
                'Image Src': '',
                'Image Position': '',
                'Image Alt Text': title,
                'Status': 'active',
            }
            rows.append(row)
        else:
            # Create rows for each image
            for idx, image_url in enumerate(images, start=1):
                row = {
                    'Handle': handle,
                    'Title': title if idx == 1 else '',  # Only show title in first row
                    'Body (HTML)': description_html if idx == 1 else '',  # Only show description in first row
                    'Vendor': default_vendor if idx == 1 else '',
                    'Type': product_type if idx == 1 else '',
                    'Tags': tags_str if idx == 1 else '',
                    'Published': 'TRUE' if idx == 1 else '',
                    'Option1 Name': '',
                    'Option1 Value': '',
                    'Variant Grams': '',
                    'Variant Inventory Qty': '' if idx == 1 else '',
                    'Variant Inventory Policy': 'deny' if idx == 1 else '',
                    'Variant Fulfillment Service': 'manual' if idx == 1 else '',
                    'Variant Price': price if idx == 1 else '',
                    'Variant Compare At Price': compare_at_price if idx == 1 else '',
                    'Variant Requires Shipping': 'TRUE' if idx == 1 else '',
                    'Variant Taxable': 'TRUE' if idx == 1 else '',
                    'Image Src': image_url,
                    'Image Position': str(idx),
                    'Image Alt Text': title,
                    'Status': 'active' if idx == 1 else '',
                }
                rows.append(row)
    
    # Write CSV file
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Converted {len(products)} products to Shopify CSV format")
    print(f"Output saved to: {output_file}")
    print(f"Total rows: {len(rows)}")


if __name__ == '__main__':
    import sys
    
    json_file = 'amazon_scrape_results.json'
    output_file = 'amazon_shopify_import.csv'
    
    # Default values
    default_price = '0.00'
    default_type = 'Book'
    default_vendor = ''
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    if len(sys.argv) > 3:
        default_price = sys.argv[3]
    if len(sys.argv) > 4:
        default_type = sys.argv[4]
    if len(sys.argv) > 5:
        default_vendor = sys.argv[5]
    
    print(f"Converting {json_file} to Shopify CSV format...")
    print(f"Default Price: {default_price}")
    print(f"Default Type: {default_type}")
    print(f"Default Vendor: {default_vendor or '(empty)'}")
    print()
    
    convert_to_shopify_csv(json_file, output_file, default_price, default_type, default_vendor)

