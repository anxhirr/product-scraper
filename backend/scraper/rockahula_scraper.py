from playwright.sync_api import Page
from scraper.base_scraper import BaseScraper
from scraper.models import Product


class RockahulaScraper(BaseScraper):
    """Scraper implementation for www.rockahulakids.com"""
    
    def get_base_url(self) -> str:
        return "https://www.rockahulakids.com/"
    
    def perform_search(self, page: Page, search_text: str, navigation_delay: float = 0) -> None:
        """Performs search on Rockahula website."""
        print(f"  → Looking for search button...")
        # Find the search icon/link in the header
        search_button = page.locator("div.t4s-site-nav__search > a, a[href='/search']").first
        search_button.wait_for(state="visible", timeout=10000)
        print(f"  ✓ Found search button")
        
        print(f"  → Clicking search button to open drawer...")
        search_button.click()
        print(f"  ✓ Clicked search button")
        
        # Wait for the search drawer to open
        print(f"  → Waiting for search drawer to open...")
        search_drawer = page.locator("#t4s-search-hidden")
        search_drawer.wait_for(state="visible", timeout=10000)
        print(f"  ✓ Search drawer is visible")
        
        # Find and fill the search input
        print(f"  → Looking for search input...")
        search_input = page.locator("input[data-input-search], input.t4s-mini-search__input").first
        search_input.wait_for(state="visible", timeout=10000)
        print(f"  ✓ Found search input")
        
        print(f"  → Filling search input with: '{search_text}'...")
        # Type the search text to trigger autocomplete
        search_input.fill(search_text)
        print(f"  ✓ Filled search input")
        
        # Wait for the search results container to appear
        print(f"  → Waiting for search results to load...")
        results_container = page.locator("div[data-results-search], div.t4s-mini-search__content")
        results_container.wait_for(state="visible", timeout=10000)
        
        # Wait a bit more for results to populate
        page.wait_for_timeout(1500)  # Wait for autocomplete/results to load
        
        # Wait for actual product results (widget__pr) to appear
        try:
            product_results = page.locator("div.t4s-widget__pr")
            product_results.first.wait_for(state="visible", timeout=10000)
            print(f"  ✓ Search results are visible")
        except:
            print(f"  ⚠ Search results may not be visible yet, continuing...")
    
    def get_first_product_link(self, page: Page, search_text: str) -> str:
        """Extracts the first product link from Rockahula search results."""
        print(f"  → Looking for product links in search results...")
        
        # Wait for search results container to be visible
        results_container = page.locator("div[data-results-search], div.t4s-mini-search__content")
        results_container.wait_for(state="visible", timeout=15000)
        print(f"  ✓ Search results container is visible")
        
        # Find product links within the search results - use the title link which is the main product link
        # This should be the actual product, not gift cards or other non-product items
        # The title link is more specific and should match the searched product
        product_links = results_container.locator("a.t4s-widget__pr-title")
        
        # If no title links found, fall back to any product link in widget__pr within results
        if product_links.count() == 0:
            print(f"  → No title links found, trying alternative selector...")
            product_links = results_container.locator("div.t4s-widget__pr a[href*='/products/']")
        
        # Wait for at least one product link to be visible
        product_links.first.wait_for(state="visible", timeout=15000)
        print(f"  ✓ Product link is visible")
        
        # Count available links to help debug
        link_count = product_links.count()
        print(f"  → Found {link_count} product link(s)")
        
        print(f"  → Extracting href attribute from first product...")
        first_product = product_links.first
        
        # Get the product title to verify it's a real product (not a gift card)
        try:
            product_title = first_product.inner_text().strip()
            print(f"  → First product title: {product_title}")
        except:
            product_title = ""
            print(f"  ⚠ Could not extract product title")
        
        # Filter out gift cards if they appear first
        if product_title and "gift" in product_title.lower() and link_count > 1:
            print(f"  ⚠ First result is a gift card, trying next product...")
            first_product = product_links.nth(1)
            try:
                product_title = first_product.inner_text().strip()
                print(f"  → Using second product: {product_title}")
            except:
                print(f"  ⚠ Could not extract second product title")
        
        href = first_product.get_attribute("href")
        print(f"  ✓ Got href: {href}")
        
        # Construct full URL if needed
        if href and href.startswith("http"):
            product_url = href
        elif href and href.startswith("/"):
            product_url = f"https://www.rockahulakids.com{href}"
        else:
            # If href is relative, construct from base URL
            product_url = f"https://www.rockahulakids.com/{href}"
        
        print(f"  ✓ Product URL: {product_url}")
        return product_url
    
    def extract_product_data(self, page: Page, product_url: str) -> Product:
        """Extracts product data from Rockahula product page."""
        print(f"  → Waiting for product title to be visible...")
        title_element = page.locator("h1.t4s-product__title")
        title_element.wait_for(state="visible", timeout=15000)
        print(f"  ✓ Product title is visible")
        
        # Extract title
        print(f"  → Extracting product title...")
        title = title_element.inner_text().strip()
        print(f"  ✓ Title: {title[:50]}..." if len(title) > 50 else f"  ✓ Title: {title}")
        
        # Extract price
        print(f"  → Extracting product price...")
        price_element = page.locator("div.t4s-product-price span.money").first
        price = price_element.inner_text().strip() if price_element.count() > 0 else ""
        if price:
            print(f"  ✓ Price: {price}")
        else:
            print(f"  ⚠ Price not found")
        
        # Extract SKU - it's in a span with class t4s-sku-value, and the text is after "Style: "
        print(f"  → Extracting product SKU...")
        sku = ""
        sku_element = page.locator("span.t4s-productMeta__value.t4s-sku-value, span.t4s-sku-value")
        if sku_element.count() > 0:
            sku = sku_element.inner_text().strip()
            print(f"  ✓ SKU: {sku}")
        else:
            # Try to find SKU in the product meta section
            sku_wrapper = page.locator("div.t4s-sku-wrapper")
            if sku_wrapper.count() > 0:
                sku_text = sku_wrapper.inner_text().strip()
                # Extract SKU after "Style: "
                if "Style:" in sku_text:
                    sku = sku_text.split("Style:")[-1].strip()
                    print(f"  ✓ SKU: {sku}")
                else:
                    print(f"  ⚠ SKU not found in expected format")
            else:
                print(f"  ⚠ SKU not found")
        
        # Extract description
        print(f"  → Extracting product description...")
        description = ""
        description_element = page.locator("div.t4s-product__description.t4s-rte")
        if description_element.count() > 0:
            description = description_element.inner_text().strip()
            description = self.normalize_text(description)
            print(f"  ✓ Description length: {len(description)} characters")
        else:
            print(f"  ⚠ Description not found")
        
        # Extract images
        print(f"  → Extracting product images...")
        images = []
        seen_urls = set()
        
        # Try to find images with data-master attribute first
        image_elements = page.locator("img[data-master]").all()
        print(f"    Found {len(image_elements)} image(s) with data-master attribute")
        
        for img in image_elements:
            src = img.get_attribute("data-master")
            if src:
                clean_url = self.clean_image_url(src)
                if clean_url and clean_url not in seen_urls:
                    seen_urls.add(clean_url)
                    images.append(clean_url)
                    print(f"      Added image: {clean_url[:60]}...")
        
        # If no images found with data-master, try regular img tags in product media section
        if not images:
            print(f"    → Trying alternative image selectors...")
            image_elements = page.locator("div[data-product-single-media-wrapper] img, div.t4s-product__media img").all()
            print(f"    Found {len(image_elements)} image element(s)")
            
            for img in image_elements:
                src = img.get_attribute("src") or img.get_attribute("data-src")
                if src:
                    clean_url = self.clean_image_url(src)
                    if clean_url and clean_url not in seen_urls:
                        seen_urls.add(clean_url)
                        images.append(clean_url)
                        print(f"      Added image: {clean_url[:60]}...")
        
        print(f"  ✓ Found {len(images)} image(s)")
        
        # Set primary image as the first image (if images exist)
        primary_image = images[0] if images else ""
        
        return Product(
            title=title,
            price=price,
            description=description,
            specifications="",  # Rockahula doesn't seem to have a separate specifications section
            images=images,
            primary_image=primary_image,
            sku=sku,
            url=product_url
        )
