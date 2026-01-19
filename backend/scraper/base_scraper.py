from abc import ABC, abstractmethod
from playwright.sync_api import Page, sync_playwright
from scraper.models import Product


class BaseScraper(ABC):
    """Abstract base class for website-specific scrapers."""
    
    @abstractmethod
    def get_base_url(self) -> str:
        """Returns the base URL of the website to scrape."""
        pass
    
    @abstractmethod
    def perform_search(self, page: Page, search_text: str) -> None:
        """Performs a search on the website using the provided search text."""
        pass
    
    @abstractmethod
    def get_first_product_link(self, page: Page, search_text: str) -> str:
        """Extracts the URL of the first product from search results."""
        pass
    
    @abstractmethod
    def extract_product_data(self, page: Page, product_url: str) -> Product:
        """Extracts all product data from the product page."""
        pass
    
    def scrape_product(self, search_text: str) -> Product:
        """
        Main scraping method that orchestrates the entire scraping flow.
        This method handles browser setup/teardown and calls the abstract methods.
        """
        print(f"[Step 1/8] Launching browser...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            print(f"[Step 2/8] Navigating to {self.get_base_url()}...")
            page.goto(self.get_base_url(), wait_until="load")
            
            print(f"[Step 3/8] Searching for '{search_text}'...")
            self.perform_search(page, search_text)
            
            print(f"[Step 4/8] Waiting for search results...")
            product_url = self.get_first_product_link(page, search_text)
            
            print(f"[Step 5/8] Navigating to product page...")
            page.goto(product_url)
            
            print(f"[Step 6/8] Waiting for product details to load...")
            # Note: Waiting for specific elements is handled in extract_product_data
            # This matches the original implementation pattern
            
            print(f"[Step 7/8] Extracting product data...")
            product = self.extract_product_data(page, product_url)
            
            print(f"[Step 8/8] Closing browser...")
            browser.close()
            
            print(f"✓ Scraping completed successfully!")
            return product
    
    @staticmethod
    def clean_image_url(url: str) -> str:
        """Helper method to clean and normalize image URLs."""
        if not url:
            return url
        # Convert protocol-relative URLs (//) to https://
        if url.startswith("//"):
            url = "https:" + url
        # Remove query parameters to get clean image URL
        clean_url = url.split("?")[0] if "?" in url else url
        return clean_url
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Helper method to normalize text by replacing newlines with spaces."""
        if not text:
            return ""
        return ' '.join(text.split())
