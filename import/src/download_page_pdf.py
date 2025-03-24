#!/usr/bin/env python3
"""
download_page_pdf.py - Downloads all PDF files linked in a given URL.

Usage:
    python download_page_pdf.py <url>
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
        response = requests.get(pdf_url, stream=True)
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

def get_pdf_links(url):
    """Extract all PDF links from a webpage."""
    try:
        # Fetch the webpage
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all links
        links = soup.find_all('a')
        
        # Extract PDF links
        pdf_links = []
        for link in links:
            href = link.get('href')
            if href:
                # Convert relative URLs to absolute URLs
                absolute_url = urljoin(url, href)
                if is_valid_pdf_url(absolute_url):
                    pdf_links.append(absolute_url)
        
        return pdf_links
    except Exception as e:
        print(f"Error fetching links from {url}: {e}")
        return []

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Download all PDFs linked in a given URL.')
    parser.add_argument('url', help='The URL to scan for PDF links')
    parser.add_argument('-o', '--output-dir', default='.', help='Directory to save PDFs (default: current directory)')
    parser.add_argument('-t', '--threads', type=int, default=5, help='Number of download threads (default: 5)')
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Get PDF links
    print(f"Scanning {args.url} for PDF links...")
    pdf_links = get_pdf_links(args.url)
    
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
