from playwright.sync_api import Page
from scraper.base_scraper import BaseScraper
from scraper.models import Product


class ElRinconDeLosGeniosScraper(BaseScraper):
    """Scraper implementation for elrincondelosgenios.com"""
    
    def get_base_url(self) -> str:
        return "https://elrincondelosgenios.com/"
    
    def perform_search(self, page: Page, search_text: str) -> None:
        """Performs search on El Rincon de los Genios website."""
        # First, click the search button to open the search dropdown
        print(f"  → Looking for search button to open search dialog...")
        search_button_selectors = [
            "#header-search-btn-drop",
            ".header-search-btn",
            "a[data-toggle='dropdown'].header-search-btn"
        ]
        
        search_button = None
        for selector in search_button_selectors:
            print(f"    Trying selector: {selector}")
            locator = page.locator(selector)
            count = locator.count()
            print(f"    Found {count} element(s)")
            if count > 0:
                search_button = locator
                print(f"  ✓ Found search button using selector: {selector}")
                break
        
        if search_button is None:
            raise Exception("Could not find search button on page")
        
        # Click the search button to open the dropdown
        print(f"  → Clicking search button to open search dialog...")
        try:
            # Use force click in case element is covered
            search_button.click(timeout=10000, force=True)
            print(f"  ✓ Clicked search button")
        except Exception as e:
            print(f"  ⚠ Click failed: {e}, trying without force...")
            try:
                search_button.click(timeout=10000)
                print(f"  ✓ Clicked search button (without force)")
            except Exception as e2:
                raise Exception(f"Failed to click search button: {e2}")
        
        # Wait a bit for the dropdown to open
        print(f"  → Waiting for dropdown to open...")
        page.wait_for_timeout(1000)  # Wait for dropdown animation
        
        # Find the search input and type directly (no need to wait for visibility or click)
        print(f"  → Looking for search input...")
        search_input = page.locator("#search_widget input[name='s']")
        if search_input.count() == 0:
            raise Exception("Could not find search input in search widget")
        
        print(f"  ✓ Found search input")
        
        # Type the search text directly (searches automatically during typing)
        print(f"  → Typing search text: '{search_text}'...")
        search_input.type(search_text, delay=100)  # Type with delay to simulate human typing
        print(f"  ✓ Typed search text (search happens automatically)")
        
        # Wait for search results to appear
        print(f"  → Waiting for search results to load...")
        page.wait_for_timeout(2000)  # Wait for search to complete
    
    def get_first_product_link(self, page: Page, search_text: str) -> str:
        """Extracts the first product link from search results (autocomplete suggestions)."""
        print(f"  → Looking for autocomplete suggestions...")
        
        # Wait for autocomplete suggestions to appear
        autocomplete_suggestions = page.locator(".autocomplete-suggestion")
        print(f"  → Waiting for autocomplete suggestions to appear...")
        try:
            autocomplete_suggestions.first.wait_for(state="visible", timeout=15000)
            print(f"  ✓ Autocomplete suggestions are visible")
        except Exception:
            print(f"  ⚠ Autocomplete suggestions visibility wait timed out, continuing...")
        
        # Count suggestions
        count = autocomplete_suggestions.count()
        print(f"    Found {count} autocomplete suggestion(s)")
        
        if count == 0:
            raise Exception("Could not find any autocomplete suggestions in search results")
        
        # Get the first suggestion's data-url attribute
        print(f"  → Extracting product URL from first suggestion...")
        first_suggestion = autocomplete_suggestions.first
        product_url = first_suggestion.get_attribute("data-url")
        
        if not product_url:
            raise Exception("First autocomplete suggestion does not have data-url attribute")
        
        print(f"  ✓ Got product URL: {product_url}")
        
        # Handle relative URLs
        if product_url.startswith("/"):
            product_url = f"https://elrincondelosgenios.com{product_url}"
        elif not product_url.startswith("http"):
            product_url = f"https://elrincondelosgenios.com/{product_url}"
        
        print(f"  ✓ Final product URL: {product_url}")
        return product_url
    
    def extract_product_data(self, page: Page, product_url: str) -> Product:
        """Extracts product data from El Rincon de los Genios product page."""
        print(f"  → Extracting product title...")
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
            print(f"    Trying selector: {selector}")
            locator = page.locator(selector).first
            if locator.count() > 0:
                title = locator.inner_text().strip()
                print(f"  ✓ Found title using selector: {selector}")
                print(f"    Title: {title[:50]}..." if len(title) > 50 else f"    Title: {title}")
                break
        
        if not title:
            raise Exception("Could not find product title")
        
        print(f"  → Extracting product price...")
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
            print(f"    Trying selector: {selector}")
            locator = page.locator(selector).first
            if locator.count() > 0:
                price = locator.inner_text().strip()
                print(f"  ✓ Found price using selector: {selector}")
                print(f"    Price: {price}")
                break
        
        if not price:
            price = "Price not available"
            print(f"  ⚠ Price not found, using default: {price}")
        
        print(f"  → Extracting product description...")
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
            print(f"    Trying selector: {selector}")
            locator = page.locator(selector).first
            if locator.count() > 0:
                description = self.normalize_text(locator.inner_text().strip())
                print(f"  ✓ Found description using selector: {selector}")
                print(f"    Description length: {len(description)} characters")
                break
        
        if not description:
            print(f"  ⚠ Description not found")
        
        print(f"  → Extracting product specifications...")
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
            print(f"    Trying selector: {selector}")
            locator = page.locator(selector)
            if locator.count() > 0:
                specifications = self.normalize_text(locator.inner_text().strip())
                print(f"  ✓ Found specifications using selector: {selector}")
                print(f"    Specifications length: {len(specifications)} characters")
                break
        
        if not specifications:
            print(f"  ⚠ Specifications not found")
        
        print(f"  → Extracting product SKU...")
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
            print(f"    Trying selector: {selector}")
            locator = page.locator(selector)
            if locator.count() > 0:
                sku = locator.inner_text().strip()
                print(f"  ✓ Found SKU using selector: {selector}")
                print(f"    SKU: {sku}")
                break
        
        if not sku:
            print(f"  ⚠ SKU not found")
        
        print(f"  → Extracting product images...")
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
            print(f"    Trying selector: {selector}")
            image_elements = page.locator(selector).all()
            if image_elements:
                print(f"    Found {len(image_elements)} image element(s)")
                for img in image_elements:
                    src = img.get_attribute("src")
                    if not src:
                        src = img.get_attribute("data-src")  # Try lazy-loaded images
                    if src:
                        clean_url = self.clean_image_url(src)
                        if clean_url and clean_url not in seen_urls:
                            seen_urls.add(clean_url)
                            images.append(clean_url)
                            print(f"      Added image: {clean_url[:60]}...")
                if images:
                    print(f"  ✓ Found {len(images)} image(s) using selector: {selector}")
                    break
        
        if not images:
            print(f"  ⚠ No images found")
        
        return Product(
            title=title,
            price=price,
            description=description,
            specifications=specifications,
            images=images,
            sku=sku,
            url=product_url
        )
