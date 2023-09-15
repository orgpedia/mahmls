import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def find_urls_containing_string(url, search_string):
    response = requests.get(url)

    if response.status_code != 200:
        print("Failed to get the webpage.")
        return

    soup = BeautifulSoup(response.text, 'html.parser')

    links = soup.find_all('a')

    matching_links = []
    for link in links:
        href = link.get('href', '')
        # Make sure the link is an absolute URL
        absolute_href = urljoin(url, href)
        if search_string in absolute_href:
            matching_links.append(absolute_href)

    return matching_links

if __name__ == "__main__":
    url = input("Enter the URL to scrape: ")
    search_string = input("Enter the string to search for in URLs: ")
    
    matching_links = find_urls_containing_string(url, search_string)

    if matching_links:
        print("\nURLs Containing the Search String:")
        for link in matching_links:
            print(link)
    else:
        print("No URLs found containing the search string.")

