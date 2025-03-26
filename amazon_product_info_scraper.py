from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time
import csv
import os
import requests

# Proxy credentials
USERNAME = "u07482d15574405cb-zone-custom-region-eu"
PASSWORD = "u07482d15574405cb"
PROXY_DNS = "170.106.118.114:2334"

class AmazonProductInfoScraper:
    def __init__(self) -> None:
        '''
        Initializes the AmazonProductInfoScraper class by setting up the Selenium driver.
        '''
        self.setup_driver()
        self.review_id = 1
        self.logged_in = False

    def get_proxy(self):
        """
        Fetches a new proxy dynamically using provided credentials.
        Returns a dictionary containing HTTP and HTTPS proxy settings.
        """
        proxy_url = f"http://{USERNAME}:{PASSWORD}@{PROXY_DNS}"
        return {"http": proxy_url, "https": proxy_url}

    def check_ip(self):
        """
        Checks and prints the current IP address to verify if the proxy is working.
        """
        proxy = self.get_proxy()
        try:
            response = requests.get("http://ip-api.com/json", proxies=proxy, timeout=10)
            ip_data = response.json()
            print(f"Current Proxy IP: {ip_data.get('query', 'Unknown')} ({ip_data.get('country', 'Unknown')})")
        except requests.exceptions.RequestException:
            print("Failed to fetch IP address. Proxy might be blocked!")

    def setup_driver(self):
        '''
        Sets up the Selenium WebDriver (Chrome) with necessary options.
        '''
        self.options = Options()
        # self.options.add_argument("--headless")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        self.options.add_argument(f"--proxy-pac-url=data:text/javascript,{{'FindProxyForURL': function(url, host) {{ return 'PROXY {PROXY_DNS}'; }}}}")

        self.driver = webdriver.Chrome(options=self.options)
        return self.driver

    # Number of stars is not working for the second link...check out why
    def basic_product_info_scraper(self, URL, timeout=10):
        '''
        Navigates to the provided Amazon product URL, scrapes basic information like title, price,
        number of reviews, and rating stars. Uses BeautifulSoup for HTML parsing.

        Args:
            URL (str): The Amazon product page URL to scrape.
        '''
        try:
            self.driver.get(URL)

            # Wait for a specific element that confirms the page has loaded
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.ID, 'title'))  # Adjust element ID as needed
            )

            # Once the page is fully loaded, retrieve the page source
            self.page_source = self.driver.page_source
            self.soup = BeautifulSoup(self.page_source, "html.parser")

        except TimeoutException:
            print(f"Error: Timeout while waiting for page to load. URL: {URL}")
        except NoSuchElementException:
            print(f"Error: Could not find the expected element on the page. URL: {URL}")
        except Exception as e:
            print(f"An error occurred: {e}")

        print("Page successfully loaded. Continuing with the code...")

        # Scrape basic product information
        try:
            # Attempt to split the URL and extract the product ID
            parts = URL.split('/dp/')
            if len(parts) > 1:
                # Further split to get the product ID
                self.product_id = parts[1].split('/')[0]
            else:
                # Handle cases where '/dp/' is not found
                print("Product ID not found in the URL")
                self.product_id = "No Product ID"
        except Exception as e:
            print(f"An error occurred: {e}")
            self.product_id = "No Product ID"

        try:
            price_whole = self.soup.find('span', class_='a-price-whole').getText()
            price_fraction = self.soup.find('span', class_='a-price-fraction').getText()
            self.price = float(f"{price_whole}{price_fraction}")
        except (AttributeError, ValueError):
            print("Price not found or in unexpected format")
            self.price = 0.0  # Default or error value

        try:
            self.number_of_reviews = self.soup.find('span', id='acrCustomerReviewText').getText().split()[0]
        except AttributeError:
            print("Number of reviews not found")
            self.number_of_reviews = "0"

        try:
            self.number_of_stars = self.soup.find('span', id='acrPopover').find('span', class_='a-size-base a-color-base').getText()
        except AttributeError:
            print("Number of stars not found")
            self.number_of_stars = "0"

        self.reviews_navigation()

    def login(self):
        ''' Logs into Amazon only if not already logged in '''
        if self.logged_in:
            print("Already logged in. Skipping login process.")
            return  # Prevent redundant login attempts

        try:
            self.email = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="ap_email"]'))
            )
            self.email.click()
            self.email.send_keys("workingandtesting@outlook.com")

            self.continue_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="continue"]'))
            )
            self.continue_button.click()

            self.password = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="ap_password"]'))
            )
            self.password.click()
            self.password.send_keys("In71948N")

            self.sign_in_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="signInSubmit"]'))
            )
            self.sign_in_button.click()

            time.sleep(3)
            self.logged_in = True  # Mark login as successful
            print("Login successful.")

        except (NoSuchElementException, TimeoutException):
            print("Already logged in or login failed.")

    def reviews_navigation(self):
        '''
        Navigates to the customer reviews section of the product page, and handles pagination to scrape reviews from multiple pages.
        '''
        self.counter = 1
        reviews = []  # Create a list to store the reviews

        # Navigating to the reviews section
        try:
            self.review_section = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "acrCustomerReviewLink"))).click()
        except (NoSuchElementException, TimeoutException):
            print("No reviews for the given item")

        # Expand to see all of the reviews
        try:
            self.see_all_reviews = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, 'reviews-medley-footer'))).find_element(By.CLASS_NAME, 'a-link-emphasis').click()
        except (NoSuchElementException, TimeoutException):
            print("There is not a single review for this item")

        self.login()

        while True:
            time.sleep(1)

            self.page_source = self.driver.page_source
            self.soup = BeautifulSoup(self.page_source, 'html.parser')

            self.reviews_scraper(reviews)

            # Go to the next page to see the rest of reviews
            try:
                self.next_page = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//li[@class='a-last']/a"))).click()
            except (NoSuchElementException, TimeoutException):
                print("Last page has been reached. Scraping of reviews is over.")
                break

            print(f"Scraping of page {self.counter} successful.")
            self.counter += 1

            time.sleep(2)

        # Save reviews after scraping all pages
        self.save_reviews_to_csv(reviews)  # Pass the reviews list here

    def reviews_scraper(self, reviews):
        '''
        Scrapes individual reviews from the current review page and appends them to the provided list.
        '''
        try:
            self.boxes = self.soup.find_all('div', class_='a-section review aok-relative')
            print(f"Found {len(self.boxes)} reviews on the page.")
        except AttributeError:
            print("Box element name not found")

        if len(self.boxes) == 0:
            print("No reviews found on this page.")

        for self.box in self.boxes:
            try:
                self.user = self.box.find('span', class_='a-profile-name').getText()
            except AttributeError:
                print("User name not found")
                self.user = "Unknown User"

            try:
                self.summary = self.box.find('a',
                                             class_='a-size-base a-link-normal review-title a-color-base review-title-content a-text-bold').find_all(
                    'span')[2].text.strip()
            except (AttributeError, IndexError):
                print("Comment title not found")
                self.summary = "No Title"

            try:
                self.score = int(float(self.box.find('a',
                                                     class_='a-size-base a-link-normal review-title a-color-base review-title-content a-text-bold').find_all(
                    'span')[0].text.strip().split("out")[0]))
            except (AttributeError, IndexError):
                print("Stars not found")
                self.score = 0

            try:
                self.HelpfulnessNumerator = self.box.find('span',
                                                          class_='a-size-base a-color-tertiary cr-vote-text').getText()
                # Check if the text says "One person found this helpful"
                if "One person" in self.HelpfulnessNumerator:
                    self.HelpfulnessNumerator = 1
                else:
                    # Extract the number of people who found the review helpful
                    self.HelpfulnessNumerator = int(self.HelpfulnessNumerator.split("people")[0].strip())
            except (AttributeError, IndexError, ValueError):
                self.HelpfulnessNumerator = 0

            try:
                self.date_of_review = \
                self.box.find('span', class_='a-size-base a-color-secondary review-date').getText().split("on")[1]
            except (AttributeError, IndexError):
                print("Date of review not found")
                self.date_of_review = "Unknown Date"

            try:
                self.verified_purchase = self.box.find('span', class_='a-size-mini a-color-state a-text-bold').getText()
            except AttributeError:
                print("Verified purchase status not found")
                self.verified_purchase = "Not Verified"

            try:
                self.comment = self.box.find('div', class_='a-row a-spacing-small review-data').getText().strip("\n")
            except AttributeError:
                print("Comment not found")
                self.comment = "No Comment"

            review = {
                'id': self.review_id,
                'Product id': self.product_id,
                'Price': self.price,
                'No. reviews': self.number_of_reviews,
                'Total grade': self.number_of_stars,
                'Username': self.user,
                'Score': self.score,
                'Helpfulness Numerator': self.HelpfulnessNumerator,
                'Summary': self.summary,
                'Date of review': self.date_of_review,
                'Verified purchase': 'Y' if self.verified_purchase == 'Verified Purchase' else 'N',
                'Comment': self.comment,
            }

            print(f"Review data: {review}")  # This will show the whole review dictionary
            print(f"Username: {review['Username']}")  # This will print the username
            reviews.append(review)  # Append the review to the reviews list
            self.review_id += 1

    def save_reviews_to_csv(self, reviews):
        '''
        Saves the list of reviews to a CSV file named `title.csv`. If the file already exists, it appends the data;
        otherwise, it creates a new file and writes the headers first.
        '''
        file_name = "amazon_reviews.csv"  # Set the file name here

        # Check if the file exists
        file_exists = os.path.exists(file_name)

        # Define the headers for the CSV
        headers = ['id', 'Product id', 'Price', 'No. reviews', 'Total grade', 'Username', 'Score', 'Helpfulness Numerator', 'Summary', 'Date of review', 'Verified purchase', 'Comment']

        # Open the CSV file in append mode if it exists, else create a new one
        with open(file_name, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)

            # If the file does not exist, write the headers first
            if not file_exists:
                writer.writeheader()

            # Write the reviews data
            for review in reviews:
                writer.writerow(review)

    def read_links(self, filename):
        '''
        Reads a text file containing URLs (one per line) and returns them as a list.

        Args:
            filename (str): The name of the file to read from.

        Returns:
            list: A list of URLs as strings.
        '''
        with open(filename, 'r') as file:
            links = file.readlines()
        return [link.strip() for link in links]


if __name__ == "__main__":
    '''
    Main execution block: It creates an instance of AmazonProductInfoScraper, reads product URLs from a file, 
    and scrapes each URL for product and review data.
    '''
    scraper = AmazonProductInfoScraper()

    scraper.check_ip()

    # file_name_input = input("Write the name of the file: ")
    file_name_input = "nokia"
    file_name_input = file_name_input.replace(" ", "-").title()

    # Read the URLs from the text file
    links = scraper.read_links('amazon_links.txt')

    for url in links:
        print(f"Scraping URL: {url}")
        scraper.basic_product_info_scraper(url)

    scraper.driver.quit()
