import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Base landing directory for IWMP data
PORTAL_URL = "https://apsac.ap.gov.in/?page_id=5285"
ROOT_FOLDER = "APSAC_All_Batches"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def get_all_batch_pages():
    """Finds links to all individual Batch pages (Batch I to V) from the main page."""
    print(f"Scanning main portal for batch sub-links: {PORTAL_URL}...")
    try:
        response = requests.get(PORTAL_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to connect to the main portal: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    batch_urls = set()
    
    # Locate links containing 'batch' or navigating to the sub-reports
    for link in soup.find_all('a'):
        href = link.get('href')
        if href and "page_id=" in href:
            text = link.text.upper()
            # Catching "Batch - I", "Batch-V", "IWMP Reports" variations
            if "BATCH" in text or "IWMP" in text:
                absolute_url = urljoin(PORTAL_URL, href)
                batch_urls.add(absolute_url)
                
    print(f"Identified {len(batch_urls)} batch page systems to parse.\n")
    return list(batch_urls)

def extract_pdfs_from_page(page_url):
    """Scrapes all valid PDF URLs from a specific batch page."""
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a')
        pdfs = set()
        
        for link in links:
            href = link.get('href')
            if href and href.lower().endswith('.pdf'):
                # Exclude unrelated layout forms or site guides
                if "IWMP" in href.upper() or "uploads" in href:
                    pdfs.add(urljoin(page_url, href))
        return list(pdfs)
    except Exception as e:
        print(f"Error reading page {page_url}: {e}")
        return []

def download_file(url):
    """Downloads the PDF and sorts it into folders by District name."""
    filename = os.path.basename(url)
    
    # Automatically determine district from filename (e.g., SRIKAKULAM_IWMP...)
    # Splits by underscore to find the leading district tag
    prefix = filename.split('_')[0].upper()
    
    # Fallback cleanup if filename starts directly with IWMP
    district_folder = prefix if len(prefix) > 4 else "GENERAL_REPORTS"
    target_dir = os.path.join(ROOT_FOLDER, district_folder)
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    filepath = os.path.join(target_dir, filename)
    
    if os.path.exists(filepath):
        print(f"-> Already exists: {filename}")
        return

    print(f"-> Downloading: {filename}")
    try:
        file_response = requests.get(url, headers=HEADERS, timeout=30)
        if file_response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(file_response.content)
            # 1-second delay to keep server requests healthy
            time.sleep(1)
        else:
            print(f"   [Error] Received status code {file_response.status_code}")
    except Exception as e:
        print(f"   [Error] Download broken: {e}")

def main():
    # Gather the dynamic batch index links
    batch_pages = get_all_batch_pages()
    
    # Fallback safeguard: Add the main URL to the list just in case some links are direct
    if PORTAL_URL not in batch_pages:
        batch_pages.append(PORTAL_URL)
        
    master_pdf_list = set()
    
    # Step 1: Discover all PDFs across all indexed pages
    for page in batch_pages:
        print(f"Checking for PDF links inside target page: {page}")
        found_pdfs = extract_pdfs_from_page(page)
        print(f"Found {len(found_pdfs)} PDFs on this page.")
        master_pdf_list.update(found_pdfs)
        
    total_discovered = len(master_pdf_list)
    print(f"\nTotal unique PDFs discovered across all batches: {total_discovered}")
    print("Starting download processing...\n")
    
    # Step 2: Download everything discovered sequentially
    for idx, pdf_url in enumerate(sorted(master_pdf_list), 1):
        print(f"[{idx}/{total_discovered}] ", end="")
        download_file(pdf_url)

    print("\nAll batch assets have been processed and structured successfully!")

if __name__ == "__main__":
    main()
