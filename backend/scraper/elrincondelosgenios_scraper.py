from playwright.sync_api import Page
from scraper.base_scraper import BaseScraper
from scraper.models import Product


class ElRinconDeLosGeniosScraper(BaseScraper):
    """Scraper implementation for elrincondelosgenios.com"""
    
    def get_base_url(self) -> str:
        return "https://elrincondelosgenios.com/"
    
    def perform_search(self, page: Page, search_text: str) -> None:
        """Performs search on El Rincon de los Genios website."""
        print(f"  Searching for '{search_text}'...")
        # First, click the search button to open the search dropdown
        search_button_selectors = [
            "#header-search-btn-drop",
            ".header-search-btn",
            "a[data-toggle='dropdown'].header-search-btn"
        ]
        
        search_button = None
        for selector in search_button_selectors:
            locator = page.locator(selector)
            if locator.count() > 0:
                search_button = locator
                break
        
        if search_button is None:
            raise Exception("Could not find search button on page")
        
        # Click the search button to open the dropdown
        try:
            # Use force click in case element is covered
            search_button.click(timeout=10000, force=True)
        except Exception as e:
            try:
                search_button.click(timeout=10000)
            except Exception as e2:
                raise Exception(f"Failed to click search button: {e2}")
        
        # Wait a bit for the dropdown to open
        page.wait_for_timeout(1000)  # Wait for dropdown animation
        
        # Find the search input and type directly (no need to wait for visibility or click)
        search_input = page.locator("#search_widget input[name='s']")
        if search_input.count() == 0:
            raise Exception("Could not find search input in search widget")
        
        # Type the search text directly (searches automatically during typing)
        search_input.type(search_text, delay=100)  # Type with delay to simulate human typing
        
        # Wait for search results to appear
        page.wait_for_timeout(2000)  # Wait for search to complete
        print(f"  ✓ Search completed")
    
    def get_first_product_link(self, page: Page, search_text: str) -> str:
        """Extracts the first product link from search results (autocomplete suggestions)."""
        # Wait for autocomplete suggestions to appear
        autocomplete_suggestions = page.locator(".autocomplete-suggestion")
        try:
            autocomplete_suggestions.first.wait_for(state="visible", timeout=15000)
        except Exception:
            pass
        
        # Count suggestions
        count = autocomplete_suggestions.count()
        
        if count == 0:
            raise Exception("Could not find any autocomplete suggestions in search results")
        
        # Get the first suggestion's data-url attribute
        first_suggestion = autocomplete_suggestions.first
        product_url = first_suggestion.get_attribute("data-url")
        
        if not product_url:
            raise Exception("First autocomplete suggestion does not have data-url attribute")
        
        # Handle relative URLs
        if product_url.startswith("/"):
            product_url = f"https://elrincondelosgenios.com{product_url}"
        elif not product_url.startswith("http"):
            product_url = f"https://elrincondelosgenios.com/{product_url}"
        
        return product_url
    
    def extract_product_data(self, page: Page, product_url: str) -> Product:
        """Extracts product data from El Rincon de los Genios product page."""
        print(f"  Extracting product data...")
        # Extract title - try common selectors
        title = ""
        title_selectors = [
            "h1.product-title",
            "h1.product__title",
            "h1[itemprop='name']",
            ".product-title h1",
            ".product__title h1",
            "h1"
        ]
        for selector in title_selectors:
            locator = page.locator(selector).first
            if locator.count() > 0:
                title = locator.inner_text().strip()
                break
        
        if not title:
            raise Exception("Could not find product title")
        
        # Extract price - try common selectors
        price = ""
        price_selectors = [
            ".price",
            ".product-price",
            ".product__price",
            "[itemprop='price']",
            ".price-current",
            ".current-price",
            "span.price"
        ]
        for selector in price_selectors:
            locator = page.locator(selector).first
            if locator.count() > 0:
                price = locator.inner_text().strip()
                break
        
        if not price:
            price = "Price not available"
        
        # Extract description - try common selectors
        description = ""
        description_selectors = [
            ".product-description",
            ".product__description",
            "[itemprop='description']",
            ".description",
            "#description",
            ".product-details"
        ]
        for selector in description_selectors:
            locator = page.locator(selector).first
            if locator.count() > 0:
                description = self.normalize_text(locator.inner_text().strip())
                break
        
        # Extract specifications - try to find specification sections
        specifications = ""
        spec_selectors = [
            ".specifications",
            ".product-specs",
            ".specs",
            "[itemprop='additionalProperty']",
            ".product-attributes"
        ]
        for selector in spec_selectors:
            locator = page.locator(selector)
            if locator.count() > 0:
                specifications = self.normalize_text(locator.inner_text().strip())
                break
        
        # Extract SKU - try common selectors
        sku = ""
        sku_selectors = [
            ".sku",
            ".product-sku",
            "[itemprop='sku']",
            ".product-code",
            "span.sku"
        ]
        for selector in sku_selectors:
            locator = page.locator(selector)
            if locator.count() > 0:
                sku = locator.inner_text().strip()
                break
        
        # Extract images - try common selectors
        images = []
        image_selectors = [
            ".product-images img",
            ".product__images img",
            ".product-gallery img",
            "[itemprop='image']",
            ".product-photos img",
            ".main-image img",
            "img.product-image"
        ]
        seen_urls = set()
        
        for selector in image_selectors:
            image_elements = page.locator(selector).all()
            if image_elements:
                for img in image_elements:
                    src = img.get_attribute("src")
                    if not src:
                        src = img.get_attribute("data-src")  # Try lazy-loaded images
                    if src:
                        clean_url = self.clean_image_url(src)
                        if clean_url and clean_url not in seen_urls:
                            seen_urls.add(clean_url)
                            images.append(clean_url)
                if images:
                    break
        
        print(f"  ✓ Product extracted")
        return Product(
            title=title,
            price=price,
            description=description,
            specifications=specifications,
            images=images,
            sku=sku,
            url=product_url
        )
