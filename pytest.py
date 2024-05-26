import time
import os
import requests
import socket
import random
import re
import csv
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from scrapy.selector import Selector


def get_random_port():
    while True:
        port = random.randint(1000, 35000)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        if result != 0:
            return port
        sock.close()

def extract_book_info(html_content, isbn):
    sel = Selector(text=html_content)
    title = sel.css('h1.MuiTypography-root::text').get(default='None').strip()
    author = sel.css('span.MuiTypography-root.MuiTypography-body1.mui-style-1plnxgp::text').get(default='None').strip()
    book_type = sel.css('p.MuiTypography-root.MuiTypography-body1.mui-style-tgrox::text').re_first(r'(eBook|Paperback)')
    original_price = sel.css('span.strike::text').re_first(r'\$(\d+\.\d+)')
    discounted_price = sel.css('p.BuyBox_sale-price__PWbkg::text').re_first(r'\$(\d+\.\d+)')
    # isbn_10 = sel.css('span.detail-label:contains("ISBN-10") + p::text').get(default='None').strip()
    isbn_10 = isbn
    published_date = sel.css('span.detail-label:contains("Published") + p::text').get(default='None').strip()
    publisher = sel.css('span.detail-label:contains("Publisher") + p::text').get(default='None').strip()
    num_pages = sel.css('span.detail-label:contains("Number of Pages") + p::text').get(default='None').strip()

    if original_price is None:
        original_price = discounted_price
        discounted_price = None

    if published_date != 'None':
        published_date = re.sub(r'\b(\d+)(st|nd|rd|th)\b', r'\1', published_date)
        published_date = datetime.strptime(published_date, "%d %B %Y").strftime("%Y-%m-%d")

    return [title, author, book_type, original_price, discounted_price, isbn_10, published_date, publisher, num_pages]

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--remote-debugging-port=9222")  # Enable remote debugging
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def scrape_book_details(driver, isbn):
    url = f"https://www.booktopia.com.au/book/{isbn}.html"
    driver.get(url)
    time.sleep(3)  # Adjust sleep time as needed

    html_content = driver.page_source
    if "The page you are trying to access no longer exists or has been moved" in html_content:
        return ["Book not found"] * 9  # Return a list with "Book not found" for all fields

    book_info = extract_book_info(html_content)
    return book_info

def main():
    isbn_list_url = 'https://drive.google.com/uc?export=download&id=1u4f-SSnZsgleZCK0533EC5VJauoFHjuM'
    response = requests.get(isbn_list_url)
    isbn_list = response.text.splitlines()[1:1000]  # Assuming first line is a header

    driver = setup_driver()
    data = []

    with ThreadPoolExecutor(max_workers=10) as executor:  # Adjust max_workers as needed
        futures = [executor.submit(scrape_book_details, driver, isbn) for isbn in isbn_list]
        for future in futures:
            data.append(future.result())
            time.sleep(1)  # Adding a short delay to avoid rate limiting

    driver.quit()

    output_file = 'bookdata_output.csv'
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Title', 'Author', 'Book Type', 'Original Price', 'Discounted Price', 'ISBN-10', 'Published Date', 'Publisher', 'Number of Pages'])
        writer.writerows(data)

    print(f"Book information saved to {output_file}")

if __name__ == '__main__':
    main()
