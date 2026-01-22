from playwright.sync_api import Page
from scraper.base_scraper import BaseScraper
from scraper.models import Product


class HapeGlobalScraper(BaseScraper):
    """Scraper implementation for global.hape.com"""
    
    def get_base_url(self) -> str:
        return "https://global.hape.com/"
    
    def perform_search(self, page: Page, search_text: str, navigation_delay: float = 0) -> None:
        """Performs search on Hape website."""
        print(f"  Searching for '{search_text}'...")
        search_button = page.locator("button.header-action-search").first
        search_button.wait_for(state="visible", timeout=10000)
        search_button.click()
        offcanvas = page.locator("#offcanvas-search-content")
        offcanvas.wait_for(state="visible", timeout=10000)
        search_input = page.locator("#offcanvas-search-content #header-main-search-input, #offcanvas-search-content input[type='search']").first
        search_input.wait_for(state="visible", timeout=10000)
        search_input.clear()
        # Type character by character to trigger the autocomplete dropdown
        search_input.type(search_text, delay=100)
        
        current_value = search_input.input_value()
        
        # If the text wasn't fully entered, try filling it directly
        if current_value != search_text:
            search_input.fill("")  # Clear first
            page.wait_for_timeout(100)
            search_input.fill(search_text)
            page.wait_for_timeout(200)
            current_value = search_input.input_value()
        
        # Wait for the listbox to appear - this is more specific than the container
        search_listbox = page.locator("#search-suggest-listbox")
        search_listbox.wait_for(state="visible", timeout=10000)
        
        # Wait for debounce period (typically 300-500ms for autocomplete)
        # Then wait a bit more to ensure results have updated for the full search text
        page.wait_for_timeout(800)
        
        # Wait for results to stabilize - check that we have product links
        product_links = page.locator("li.search-suggest-product a.search-suggest-product-link")
        try:
            product_links.first.wait_for(state="visible", timeout=5000)
        except Exception as e:
            # Wait a bit more in case results are still loading
            page.wait_for_timeout(500)
        
        print(f"  ✓ Search completed")
    
    def get_first_product_link(self, page: Page, search_text: str) -> str:
        """Extracts the first product link from Hape search results dropdown."""
        # Wait for the listbox to be visible and have items
        search_listbox = page.locator("#search-suggest-listbox")
        search_listbox.wait_for(state="visible", timeout=10000)
        product_links = page.locator("li.search-suggest-product a.search-suggest-product-link")
        product_links.first.wait_for(state="visible", timeout=10000)
        link_count = product_links.count()
        
        if link_count == 0:
            raise Exception("No product links found in search suggest dropdown")
        
        first_product = product_links.first
        first_product.wait_for(state="visible", timeout=15000)
        href = first_product.get_attribute("href")
        
        if href and href.startswith("http"):
            product_url = href
        elif href:
            product_url = f"https://global.hape.com{href}" if href.startswith("/") else f"https://global.hape.com/{href}"
        else:
            raise Exception("Product link has no href attribute")
        return product_url
    
    def extract_product_data(self, page: Page, product_url: str) -> Product:
        """Extracts product data from Hape product page."""
        print(f"  Extracting product data...")
        title_element = page.locator("h1.product-detail-name")
        title_element.wait_for(state="visible", timeout=15000)
        
        # Extract title
        title = page.locator("h1.product-detail-name").inner_text().strip()
        
        # Extract price - use first if multiple prices exist
        price_elements = page.locator("p.product-detail-price, span.product-price")
        price_count = price_elements.count()
        if price_count > 0:
            price = price_elements.first.inner_text().strip()
        else:
            price = ""
        
        # Extract description from description accordion
        description = ""
        specifications = ""
        
        # Look for description in the description accordion
        description_el = page.locator(".description-accordion-content-description-text")
        description_count = description_el.count()
        if description_count > 0:
            description = description_el.first.inner_text().strip()
            description = self.normalize_text(description)
        
        # Extract Specifications section
        try:
            # Find the Specifications accordion by looking for accordion with "Specifications" text
            specs_accordion = page.locator(".description-accordion-item").filter(has_text="Specifications")
            specs_count = specs_accordion.count()
            if specs_count > 0:
                # Find the container with specification items
                specs_items_container = specs_accordion.first.locator(".description-accordion-content-items")
                if specs_items_container.count() > 0:
                    # Get all specification items
                    spec_items = specs_items_container.first.locator(".description-accordion-content-item").all()
                    
                    spec_lines = []
                    for item in spec_items:
                        # Each item has two spans: key and value
                        spans = item.locator("span").all()
                        if len(spans) >= 2:
                            key = spans[0].inner_text().strip()
                            value = spans[1].inner_text().strip()
                            # Skip Title, Barcode, Category, Quantity, and Product number fields as they're redundant
                            key_lower = key.lower()
                            skip_fields = ["title", "barcode", "category", "quantity", "product number", "productnumber", "numri i produktit"]
                            if key and value and key_lower not in skip_fields:
                                spec_lines.append(f"{key}: {value}")
                    
                    if spec_lines:
                        specifications = "\n".join(spec_lines)
                        # Don't normalize specifications - preserve newlines for proper parsing
        except Exception:
            pass
        
        # Extract SKU from product meta
        sku_el = page.locator("span.description-accordion-content-ordernumber")
        sku_count = sku_el.count()
        if sku_count > 0:
            sku = sku_el.first.inner_text().strip()
        else:
            sku = ""
        
        # Extract images from gallery slider
        image_elements = page.locator(".gallery-slider-image[src], .gallery-slider-image[data-src]").all()
        images = []
        seen_urls = set()
        
        for i, img in enumerate(image_elements, 1):
            # Try src first, then data-src
            src = img.get_attribute("src")
            if not src:
                src = img.get_attribute("data-src")
            if src:
                clean_url = self.clean_image_url(src)
                if clean_url not in seen_urls:
                    seen_urls.add(clean_url)
                    images.append(clean_url)
        
        # Set primary image as the first image (if images exist)
        primary_image = images[0] if images else ""
        
        product = Product(
            title=title,
            price=price,
            description=description,
            specifications=specifications,
            images=images,
            primary_image=primary_image,
            sku=sku,
            url=product_url
        )
        
        print(f"  ✓ Product extracted")
        return product
