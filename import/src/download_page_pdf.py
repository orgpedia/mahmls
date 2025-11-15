#!/usr/bin/env python3
"""
download_page_pdf.py - Downloads all PDF files linked in a given URL or HTML file.

Usage:
    python download_page_pdf.py <url_or_file> [-o OUTPUT_DIR] [-t THREADS] [-b BASE_URL]

Examples:
    python download_page_pdf.py https://example.com/page.html
    python download_page_pdf.py page.html -b https://example.com
"""

import os
import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import argparse
import concurrent.futures

def is_valid_pdf_url(url):
    """Check if URL points to a PDF file."""
    parsed = urlparse(url)
    return parsed.path.lower().endswith('.pdf')

def get_headers():
    """Return headers that mimic a real browser."""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }

def download_pdf(pdf_url, output_dir='.'):
    """Download a PDF file and save it to the specified directory."""
    try:
        # Extract filename from URL
        filename = os.path.basename(urlparse(pdf_url).path)
        # Ensure filename is not empty
        if not filename:
            filename = f"document_{hash(pdf_url)}.pdf"

        output_path = os.path.join(output_dir, filename)

        # Check if file already exists
        if os.path.exists(output_path):
            print(f"File already exists: {filename}")
            return None

        # Download the PDF
        print(f"Downloading: {filename} from {pdf_url}")
        response = requests.get(pdf_url, headers=get_headers(), stream=True)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Check if content is actually a PDF
        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/pdf' not in content_type and not pdf_url.lower().endswith('.pdf'):
            print(f"Warning: {pdf_url} might not be a PDF (Content-Type: {content_type})")
        
        # Save the PDF
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        print(f"Downloaded: {filename}")
        return output_path
    except Exception as e:
        print(f"Error downloading {pdf_url}: {e}")
        return None

def get_pdf_links_from_html(html_content, base_url):
    """Extract all PDF links from HTML content."""
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find all links
    links = soup.find_all('a')

    # Extract PDF links
    pdf_links = []
    for link in links:
        href = link.get('href')
        if href:
            # Convert relative URLs to absolute URLs
            absolute_url = urljoin(base_url, href)
            if is_valid_pdf_url(absolute_url):
                pdf_links.append(absolute_url)

    return pdf_links

def get_pdf_links(source, output_dir='.', base_url=None):
    """Extract all PDF links from a webpage URL or HTML file.

    Args:
        source: Either a URL or a file path
        output_dir: Directory to save files
        base_url: Base URL for resolving relative links (required if source is a file)
    """
    try:
        # Check if source is a file
        if os.path.isfile(source):
            print(f"Reading HTML from file: {source}")
            with open(source, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Use base_url if provided, otherwise use empty string
            if not base_url:
                print("Warning: No base URL provided for resolving relative links")
                base_url = ''

            return get_pdf_links_from_html(html_content, base_url)
        else:
            # Treat as URL
            print(f"Fetching HTML from URL: {source}")
            response = requests.get(source, headers=get_headers())
            response.raise_for_status()

            # Ensure proper encoding
            response.encoding = response.apparent_encoding or 'utf-8'

            # Save HTML content
            html_filename = os.path.join(output_dir, 'page.html')
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"Saved HTML to: {html_filename}")

            return get_pdf_links_from_html(response.text, source)
    except Exception as e:
        print(f"Error processing {source}: {e}")
        return []

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Download all PDFs linked in a given URL or HTML file.')
    parser.add_argument('source', help='The URL or HTML file path to scan for PDF links')
    parser.add_argument('-o', '--output-dir', default='.', help='Directory to save PDFs (default: current directory)')
    parser.add_argument('-t', '--threads', type=int, default=5, help='Number of download threads (default: 5)')
    parser.add_argument('-b', '--base-url', help='Base URL for resolving relative links (required when using a file)')
    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    # Get PDF links
    print(f"Scanning {args.source} for PDF links...")
    pdf_links = get_pdf_links(args.source, args.output_dir, args.base_url)
    
    if not pdf_links:
        print("No PDF links found.")
        return
    
    print(f"Found {len(pdf_links)} PDF links.")
    
    # Download PDFs in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = [executor.submit(download_pdf, pdf_url, args.output_dir) for pdf_url in pdf_links]
        
        # Wait for all downloads to complete
        downloaded_files = []
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                downloaded_files.append(result)
    
    print(f"\nDownload summary:")
    print(f"Total PDF links found: {len(pdf_links)}")
    print(f"Successfully downloaded: {len(downloaded_files)}")
    print(f"Failed or skipped: {len(pdf_links) - len(downloaded_files)}")

if __name__ == "__main__":
    main()
