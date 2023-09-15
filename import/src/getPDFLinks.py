import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import sys

def download_pdf(url, directory=''):
    try:
        r = requests.get(url)
        if r.status_code == 200 and 'application/pdf' in r.headers['Content-Type']:
            # Parse the filename from the URL path
            path = urlparse(url).path
            filename = os.path.basename(path)
            
            # Create directory if it doesn't exist
            if directory:
                os.makedirs(directory, exist_ok=True)
                
            full_filename = os.path.join(directory, filename)
            with open(full_filename, 'wb') as f:
                f.write(r.content)
            print(f"Downloaded: {filename}")
        else:
            print(f"Failed to download: {url}")
    except Exception as e:
        print(f"An error occurred while downloading {url}: {e}")

def find_and_download_pdfs(base_url):
    response = requests.get(base_url)
    
    if response.status_code != 200:
        print("Failed to get the webpage")
        return
    
    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.find_all('a')

    for link in links:
        href = link.get('href', '')
        if href.endswith('.pdf'):
            absolute_href = urljoin(base_url, href)
            
            # Replicate the directory structure
            parsed_url = urlparse(absolute_href)
            directory_structure = os.path.dirname(parsed_url.path).lstrip('/')
            
            download_pdf(absolute_href, directory=directory_structure)

if __name__ == "__main__":
    url = sys.argv[1]
    find_and_download_pdfs(url)

