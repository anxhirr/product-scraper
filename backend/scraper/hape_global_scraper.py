from playwright.sync_api import Page
from scraper.base_scraper import BaseScraper
from scraper.models import Product


class HapeGlobalScraper(BaseScraper):
    """Scraper implementation for global.hape.com"""
    
    def get_base_url(self) -> str:
        return "https://global.hape.com/"
    
    def perform_search(self, page: Page, search_text: str) -> None:
        """Performs search on Hape website."""
        print(f"  → Starting search process for: '{search_text}'")
        print(f"  → Step 1: Looking for desktop search button (header-action-search)...")
        search_button = page.locator("button.header-action-search").first
        print(f"  → Step 2: Waiting for search button to be visible...")
        search_button.wait_for(state="visible", timeout=10000)
        print(f"  ✓ Search button is visible")
        print(f"  → Step 3: Clicking search button to open offcanvas search panel...")
        search_button.click()
        print(f"  ✓ Search button clicked")
        print(f"  → Step 4: Waiting for offcanvas search panel to open...")
        offcanvas = page.locator("#offcanvas-search-content")
        offcanvas.wait_for(state="visible", timeout=10000)
        print(f"  ✓ Offcanvas search panel is now visible")
        print(f"  → Step 5: Waiting for search input inside offcanvas to become visible...")
        search_input = page.locator("#offcanvas-search-content #header-main-search-input, #offcanvas-search-content input[type='search']").first
        search_input.wait_for(state="visible", timeout=10000)
        print(f"  ✓ Search input is now visible")
        print(f"  → Step 6: Checking if search input is enabled...")
        is_enabled = search_input.is_enabled()
        print(f"  ✓ Search input enabled: {is_enabled}")
        print(f"  → Step 7: Clearing any existing text in search input...")
        search_input.clear()
        print(f"  ✓ Search input cleared")
        print(f"  → Step 8: Typing search text character by character to trigger autocomplete: '{search_text}'...")
        # Type character by character to trigger the autocomplete dropdown
        search_input.type(search_text, delay=100)
        print(f"  ✓ Search text typed")
        
        print(f"  → Step 9: Verifying search text was entered completely...")
        current_value = search_input.input_value()
        print(f"  ✓ Current search input value: '{current_value}'")
        
        # If the text wasn't fully entered, try filling it directly
        if current_value != search_text:
            print(f"  ⚠ Text mismatch detected. Expected: '{search_text}', Got: '{current_value}'")
            print(f"  → Retrying by filling the input directly...")
            search_input.fill("")  # Clear first
            page.wait_for_timeout(100)
            search_input.fill(search_text)
            page.wait_for_timeout(200)
            current_value = search_input.input_value()
            print(f"  ✓ After retry, current search input value: '{current_value}'")
        
        print(f"  → Step 10: Waiting for search suggest dropdown to appear...")
        # Wait for the listbox to appear - this is more specific than the container
        search_listbox = page.locator("#search-suggest-listbox")
        search_listbox.wait_for(state="visible", timeout=10000)
        print(f"  ✓ Search suggest listbox is now visible")
        
        print(f"  → Step 11: Waiting for autocomplete debounce to complete and results to stabilize...")
        # Wait for debounce period (typically 300-500ms for autocomplete)
        # Then wait a bit more to ensure results have updated for the full search text
        page.wait_for_timeout(800)
        print(f"  ✓ Debounce wait completed")
        
        print(f"  → Step 12: Waiting for product items to populate with final search results...")
        # Wait for results to stabilize - check that we have product links
        product_links = page.locator("li.search-suggest-product a.search-suggest-product-link")
        try:
            product_links.first.wait_for(state="visible", timeout=5000)
            link_count = product_links.count()
            print(f"  ✓ Found {link_count} product link(s) after debounce")
        except Exception as e:
            print(f"  ⚠ No product links found yet: {e}")
            # Wait a bit more in case results are still loading
            page.wait_for_timeout(500)
            link_count = product_links.count()
            print(f"  ✓ After additional wait, found {link_count} product link(s)")
        
        print(f"  ✓ Search results stabilized for search text: '{search_text}'")
    
    def get_first_product_link(self, page: Page, search_text: str) -> str:
        """Extracts the first product link from Hape search results dropdown."""
        print(f"  → Step 1: Getting current page URL...")
        current_url = page.url
        print(f"  ✓ Current URL: {current_url}")
        print(f"  → Step 2: Looking for search suggest listbox...")
        # Wait for the listbox to be visible and have items
        search_listbox = page.locator("#search-suggest-listbox")
        print(f"  → Step 3: Waiting for search suggest listbox to be visible...")
        search_listbox.wait_for(state="visible", timeout=10000)
        print(f"  ✓ Search suggest listbox is visible")
        print(f"  → Step 4: Looking for product links in search suggest dropdown...")
        product_links = page.locator("li.search-suggest-product a.search-suggest-product-link")
        print(f"  → Step 5: Waiting for at least one product link to appear...")
        product_links.first.wait_for(state="visible", timeout=10000)
        link_count = product_links.count()
        print(f"  ✓ Found {link_count} product link(s) in dropdown")
        
        if link_count == 0:
            raise Exception("No product links found in search suggest dropdown")
        
        print(f"  → Step 6: Selecting first product link...")
        first_product = product_links.first
        print(f"  → Step 7: Waiting for first product link to be visible...")
        first_product.wait_for(state="visible", timeout=15000)
        print(f"  ✓ First product link is visible")
        print(f"  → Step 8: Extracting href attribute from first product link...")
        href = first_product.get_attribute("href")
        print(f"  ✓ Got href: {href}")
        print(f"  → Step 9: Constructing full product URL...")
        if href and href.startswith("http"):
            product_url = href
        elif href:
            product_url = f"https://global.hape.com{href}" if href.startswith("/") else f"https://global.hape.com/{href}"
        else:
            raise Exception("Product link has no href attribute")
        print(f"  ✓ Product URL: {product_url}")
        return product_url
    
    def extract_product_data(self, page: Page, product_url: str) -> Product:
        """Extracts product data from Hape product page."""
        print(f"  → Step 1: Getting current page URL...")
        current_url = page.url
        print(f"  ✓ Current URL: {current_url}")
        print(f"  → Step 2: Waiting for product title to be visible...")
        title_element = page.locator("h1.product-detail-name")
        title_element.wait_for(state="visible", timeout=15000)
        print(f"  ✓ Product title element is visible")
        
        # Extract title
        print(f"  → Step 3: Extracting product title text...")
        title = page.locator("h1.product-detail-name").inner_text().strip()
        print(f"  ✓ Title extracted: {title[:50]}..." if len(title) > 50 else f"  ✓ Title extracted: {title}")
        print(f"  → Step 4: Title length: {len(title)} characters")
        
        # Extract price - use first if multiple prices exist
        print(f"  → Step 5: Looking for product price element...")
        price_elements = page.locator("p.product-detail-price, span.product-price")
        price_count = price_elements.count()
        print(f"  ✓ Found {price_count} price element(s)")
        if price_count > 0:
            print(f"  → Step 6: Extracting first price...")
            price = price_elements.first.inner_text().strip()
            print(f"  ✓ Price extracted: {price}")
        else:
            print(f"  ⚠ Step 6: No price element found, setting price to empty string")
            price = ""
        
        # Extract description from description accordion
        print(f"  → Step 7: Looking for description accordion...")
        description = ""
        specifications = ""
        
        # Look for description in the description accordion
        print(f"  → Step 8: Looking for description text in accordion...")
        description_el = page.locator(".description-accordion-content-description-text")
        description_count = description_el.count()
        print(f"  ✓ Found {description_count} description element(s)")
        if description_count > 0:
            print(f"  → Step 9: Extracting description text...")
            description = description_el.first.inner_text().strip()
            description = self.normalize_text(description)
            print(f"  ✓ Description extracted, length: {len(description)} characters")
        
        # Extract Features section as specifications
        print(f"  → Step 10: Looking for Features accordion...")
        try:
            # Find the Features accordion by looking for accordion with "Features" text
            features_accordion = page.locator(".description-accordion-item").filter(has_text="Features")
            features_count = features_accordion.count()
            print(f"  ✓ Found {features_count} Features accordion(s)")
            if features_count > 0:
                print(f"  → Step 11: Extracting Features content...")
                features_content = features_accordion.first.locator(".description-accordion-content-inner ul")
                if features_content.count() > 0:
                    specs_text = features_content.first.inner_text().strip()
                    specifications = self.normalize_text(specs_text)
                    print(f"  ✓ Features section extracted")
                    print(f"  ✓ Specifications length: {len(specifications)} characters")
                else:
                    # Try without ul, just get the inner text
                    features_inner = features_accordion.first.locator(".description-accordion-content-inner")
                    if features_inner.count() > 0:
                        specs_text = features_inner.first.inner_text().strip()
                        specifications = self.normalize_text(specs_text)
                        print(f"  ✓ Features section extracted (without ul)")
                        print(f"  ✓ Specifications length: {len(specifications)} characters")
        except Exception as e:
            print(f"  ⚠ Features section not found: {str(e)}")
        
        if not description:
            print(f"  ⚠ Step 12: Description not found")
        
        # Extract SKU from product meta
        print(f"  → Step 13: Looking for product SKU element...")
        sku_el = page.locator("span.description-accordion-content-ordernumber")
        sku_count = sku_el.count()
        print(f"  ✓ Found {sku_count} SKU element(s)")
        if sku_count > 0:
            print(f"  → Step 14: Extracting SKU text...")
            sku = sku_el.first.inner_text().strip()
            print(f"  ✓ SKU extracted: {sku}")
        else:
            print(f"  ⚠ SKU not found")
            sku = ""
        
        # Extract images from gallery slider
        print(f"  → Step 15: Looking for product images in gallery slider...")
        image_elements = page.locator(".gallery-slider-image[src], .gallery-slider-image[data-src]").all()
        print(f"  ✓ Found {len(image_elements)} image element(s)")
        images = []
        seen_urls = set()
        
        print(f"  → Step 16: Processing images...")
        for i, img in enumerate(image_elements, 1):
            print(f"    → Processing image {i}/{len(image_elements)}...")
            # Try src first, then data-src
            src = img.get_attribute("src")
            if not src:
                src = img.get_attribute("data-src")
            if src:
                print(f"    ✓ Image {i} src: {src[:60]}...")
                print(f"    → Cleaning image URL...")
                clean_url = self.clean_image_url(src)
                print(f"    ✓ Cleaned URL: {clean_url[:60]}...")
                if clean_url not in seen_urls:
                    seen_urls.add(clean_url)
                    images.append(clean_url)
                    print(f"    ✓ Added image {i} to list (total: {len(images)})")
                else:
                    print(f"    ⚠ Image {i} already in list, skipping duplicate")
            else:
                print(f"    ⚠ Image {i} has no src or data-src attribute, skipping")
        
        print(f"  ✓ Step 17: Image extraction complete, found {len(images)} unique image(s)")
        
        print(f"  → Step 18: Creating Product object...")
        print(f"    → Title: {title[:50]}..." if len(title) > 50 else f"    → Title: {title}")
        print(f"    → Price: {price}")
        print(f"    → Description length: {len(description)} characters")
        print(f"    → Specifications length: {len(specifications)} characters")
        print(f"    → SKU: {sku}")
        print(f"    → Images: {len(images)}")
        print(f"    → URL: {product_url}")
        
        product = Product(
            title=title,
            price=price,
            description=description,
            specifications=specifications,
            images=images,
            sku=sku,
            url=product_url
        )
        
        print(f"  ✓ Step 21: Product object created successfully")
        return product
