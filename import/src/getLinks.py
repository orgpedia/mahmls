import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import xlsxwriter

def find_pdf_links(url):
    response = requests.get(url)
    
    if response.status_code != 200:
        print("Failed to get the webpage")
        return
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    links = soup.find_all('a')
    
    pdf_links = []
    for link in links:
        href = link.get('href', '')
        if href.endswith('.pdf'):
            # Make sure the link is an absolute URL
            absolute_href = urljoin(url, href)
            pdf_links.append((link.string if link.string else 'N/A', absolute_href))
    
    return pdf_links

if __name__ == "__main__":
    url = input("Enter the URL to scrape for PDF links: ")
    pdf_links = find_pdf_links(url)
    
    # Create an Excel workbook and add a worksheet
    workbook = xlsxwriter.Workbook('pdf_links.xlsx')
    worksheet = workbook.add_worksheet()
    
    # Add headers
    worksheet.write('A1', 'Title')
    worksheet.write('B1', 'URL')
    
    if pdf_links:
        # Write data to Excel sheet
        for i, (title, link) in enumerate(pdf_links, start=1):
            worksheet.write(f'A{i+1}', title)
            worksheet.write(f'B{i+1}', link)
        
        print("PDF links have been written to 'pdf_links.xlsx'")
    else:
        print("No PDF links found.")
    
    # Close workbook
    workbook.close()

