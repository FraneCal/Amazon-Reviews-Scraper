from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import subprocess
import time
import os


class AmazonProductLinksScraper():
    def __init__(self) -> None:
        ''' Initializes Selenium WebDriver and an empty list for storing links. '''
        self.setup_driver()
        self.links_list = []

    def setup_driver(self):
        ''' Configures the Selenium WebDriver (Chrome) '''
        self.options = Options()
        self.options.add_argument("--headless")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(options=self.options)
        self.driver.maximize_window()

    def scrolling_and_pagination(self, URL):
        ''' Automates scrolling and paginating through search results '''
        self.driver.get(URL)
        time.sleep(2)

        page_count = 1

        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

            self.scraping()

            try:
                self.next_page = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(@aria-label, 'Go to next page')]"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", self.next_page)
                time.sleep(1)
                self.next_page.click()
            except (NoSuchElementException, TimeoutException):
                print("Last page reached. Scraping complete.")
                break

            print(f"Scraped page {page_count} successfully.")
            page_count += 1

    def scraping(self):
        ''' Extracts product links from the current page '''
        time.sleep(2)  # Ensure page loads before scraping

        # Use Selenium to find links directly
        product_links = self.driver.find_elements(By.XPATH, "//a[contains(@class, 'a-link-normal s-underline-text')]")

        new_links = []
        for link in product_links:
            href = link.get_attribute('href')
            if href and href.startswith("https://www.amazon."):
                if href not in self.links_list:  # Avoid duplicates
                    self.links_list.append(href)
                    new_links.append(href)

        if not new_links:
            print("No new links found on this page. Check if elements are loading correctly.")

        # Write collected links to the file
        with open("amazon_links.txt", 'a') as f:  # 'a' mode to append, not overwrite
            for link in new_links:
                f.write(f"{link}\n")


def remove_duplicates():
    ''' Reads amazon_links.txt, removes duplicates, and saves only unique links '''
    if os.path.exists("amazon_links.txt"):
        with open("amazon_links.txt", "r") as f:
            links = f.readlines()

        unique_links = sorted(set(link.strip() for link in links))  # Remove duplicates & sort

        if len(unique_links) == len(links):  # Check if any duplicates were removed
            print("No duplicates found. File remains unchanged.")
        else:
            with open("amazon_links.txt", "w") as f:
                for link in unique_links:
                    f.write(link + "\n")
            print(f"Removed duplicates. Final link count: {len(unique_links)}")


if __name__ == "__main__":
    URL = "https://www.amazon.com/s?k=nokia+3310"

    scraper = AmazonProductLinksScraper()
    scraper.scrolling_and_pagination(URL)

    print("Scraping complete, checking for duplicates...")
    remove_duplicates()  # Call function to remove duplicates

    print("Calling amazon_product_info_scraper.py...")
    scraper.driver.quit()

    subprocess.run(["python", "amazon_product_info_scraper.py"])
