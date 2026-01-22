from playwright.sync_api import Page
import time
from scraper.base_scraper import BaseScraper
from scraper.models import Product


class DoneByDeerScraper(BaseScraper):
    """Scraper implementation for donebydeer.com"""
    
    def get_base_url(self) -> str:
        return "https://donebydeer.com"
    
    def perform_search(self, page: Page, search_text: str, navigation_delay: float = 0) -> None:
        """Performs search on Done by Deer website using barcode."""
        # Set desktop viewport to ensure desktop search button is visible
        # Desktop search button is hidden on mobile, so we need desktop viewport
        page.set_viewport_size({"width": 1920, "height": 1080})
        # Wait for viewport change to take effect and CSS to re-evaluate
        page.wait_for_timeout(1000)
        
        # Handle cookie consent overlay if present
        print(f"  → Checking for cookie consent overlay...")
        cookie_overlay = page.locator("#coiOverlay, .coiOverlay-container, #cookie-information-template-wrapper")
        if cookie_overlay.count() > 0:
            try:
                # Wait for overlay to be visible
                cookie_overlay.first.wait_for(state="visible", timeout=3000)
                print(f"  → Cookie overlay detected, trying to dismiss...")
                
                # Try to find and click accept/dismiss button
                # Common selectors for cookie consent buttons
                accept_selectors = [
                    'button:has-text("Accept")',
                    'button:has-text("Accept All")',
                    'button:has-text("I Accept")',
                    'button:has-text("Accept Cookies")',
                    'button:has-text("Godkend")',  # Danish for Accept
                    'button:has-text("Accepter")',  # Danish for Accept
                    '[aria-label*="Accept"]',
                    '[aria-label*="accept"]',
                    '.coi-banner__accept',
                    '#coiAcceptButton',
                    'button.coi-banner__accept',
                ]
                
                dismissed = False
                for selector in accept_selectors:
                    try:
                        accept_button = page.locator(selector).first
                        if accept_button.count() > 0 and accept_button.is_visible(timeout=1000):
                            accept_button.click()
                            print(f"  ✓ Clicked cookie accept button")
                            # Wait for overlay to disappear
                            page.wait_for_timeout(500)
                            dismissed = True
                            break
                    except:
                        continue
                
                if not dismissed:
                    # Try to hide overlay by setting aria-hidden and display none
                    try:
                        page.evaluate("""
                            const overlay = document.getElementById('coiOverlay');
                            if (overlay) {
                                overlay.setAttribute('aria-hidden', 'true');
                                overlay.style.display = 'none';
                            }
                            const container = document.querySelector('.coiOverlay-container');
                            if (container) {
                                container.setAttribute('aria-hidden', 'true');
                                container.style.display = 'none';
                            }
                            const wrapper = document.getElementById('cookie-information-template-wrapper');
                            if (wrapper) {
                                wrapper.style.display = 'none';
                            }
                        """)
                        print(f"  ✓ Hid cookie overlay programmatically")
                        page.wait_for_timeout(500)
                    except:
                        pass
                
                # Wait a bit more and verify overlay is gone
                page.wait_for_timeout(500)
            except:
                print(f"  ⚠ Cookie overlay handling failed, continuing...")
        
        # Verify cookie overlay is not blocking (wait for it to be hidden or removed)
        try:
            cookie_overlay_check = page.locator("#coiOverlay[aria-hidden='false'], .coiOverlay-container[aria-hidden='false']")
            if cookie_overlay_check.count() > 0:
                print(f"  → Cookie overlay still visible, waiting for it to disappear...")
                cookie_overlay_check.first.wait_for(state="hidden", timeout=5000)
        except:
            pass  # Overlay might already be gone
        
        print(f"  → Looking for search button...")
        
        # Find the search button/link in the header
        # The desktop search button is in .header__secondary-links and has classes "hidden-pocket hidden-lap"
        # The mobile search button has class "hidden-desk" (hidden on desktop)
        # Try desktop version first (in secondary links section)
        search_button = page.locator('.header__secondary-links a[href*="/search"]').first
        
        # Check if desktop search button is visible
        try:
            search_button.wait_for(state="visible", timeout=5000)
            print(f"  ✓ Found desktop search button")
        except:
            # Fallback: try to find any visible search link
            print(f"  → Desktop search button not visible, trying alternative...")
            all_search_links = page.locator('a[href*="/search"]').all()
            found = False
            for link in all_search_links:
                try:
                    if link.is_visible(timeout=1000):
                        search_button = link
                        found = True
                        print(f"  ✓ Found visible search button")
                        break
                except:
                    continue
            
            if not found:
                # Last resort: try the secondary links selector again
                search_button = page.locator('.header__secondary-links a[href*="/search"]').first
                search_button.wait_for(state="visible", timeout=10000)
                print(f"  ✓ Found search button (fallback)")
        
        print(f"  → Clicking search button to open drawer...")
        # Ensure button is actionable before clicking
        search_button.wait_for(state="visible", timeout=5000)
        
        # Try normal click first
        try:
            search_button.click(timeout=10000)
            print(f"  ✓ Clicked search button")
        except Exception as e:
            # If normal click fails (e.g., due to overlay), try JavaScript click
            print(f"  → Normal click failed ({str(e)[:50]}...), trying JavaScript click...")
            try:
                search_button.evaluate("element => element.click()")
                print(f"  ✓ Clicked search button via JavaScript")
            except:
                # Last resort: force click
                print(f"  → JavaScript click failed, trying force click...")
                search_button.click(force=True)
                print(f"  ✓ Clicked search button (force)")
        
        # Wait for the search drawer to open
        print(f"  → Waiting for search drawer to open...")
        search_drawer = page.locator("#search-drawer, predictive-search-drawer#search-drawer")
        search_drawer.wait_for(state="visible", timeout=10000)
        print(f"  ✓ Search drawer is visible")
        
        # Wait a bit for drawer animation
        page.wait_for_timeout(500)
        
        # Find and fill the search input
        print(f"  → Looking for search input...")
        search_input = page.locator('input[name="q"]').first
        search_input.wait_for(state="visible", timeout=10000)
        print(f"  ✓ Found search input")
        
        print(f"  → Filling search input with barcode: '{search_text}'...")
        # Clear and type the barcode to trigger search
        search_input.fill(search_text)
        print(f"  ✓ Filled search input")
        
        # Wait for the search results to appear
        print(f"  → Waiting for search results to load...")
        results_container = page.locator(".predictive-search__results")
        results_container.wait_for(state="visible", timeout=10000)
        
        # Wait for product list to appear
        product_list = page.locator("ul.predictive-search__product-list")
        product_list.wait_for(state="visible", timeout=10000)
        
        # Wait a bit more for results to populate
        page.wait_for_timeout(1500)  # Wait for autocomplete/results to load
        
        # Wait for actual product items to appear
        try:
            product_items = page.locator("li.predictive-search__product-item")
            product_items.first.wait_for(state="visible", timeout=10000)
            print(f"  ✓ Search results are visible")
        except:
            print(f"  ⚠ Search results may not be visible yet, continuing...")
    
    def get_first_product_link(self, page: Page, search_text: str) -> str:
        """Extracts the first product link from Done by Deer search results drawer."""
        print(f"  → Looking for product links in search results...")
        
        # Wait for search results container to be visible
        results_container = page.locator(".predictive-search__results")
        results_container.wait_for(state="visible", timeout=15000)
        print(f"  ✓ Search results container is visible")
        
        # Find product links within the search results
        product_links = page.locator("li.predictive-search__product-item a.line-item__content-wrapper")
        
        # If no links found with that selector, try alternative
        if product_links.count() == 0:
            print(f"  → No links found with primary selector, trying alternative...")
            product_links = page.locator("ul.predictive-search__product-list a[href*='/products/']")
        
        # Wait for at least one product link to be visible
        product_links.first.wait_for(state="visible", timeout=15000)
        print(f"  ✓ Product link is visible")
        
        # Count available links to help debug
        link_count = product_links.count()
        print(f"  → Found {link_count} product link(s)")
        
        print(f"  → Extracting href attribute from first product...")
        first_product = product_links.first
        
        # Get the product title to verify it's a real product
        try:
            product_title_element = first_product.locator(".product-item-meta__title, .line-item__info .product-item-meta__title")
            if product_title_element.count() > 0:
                product_title = product_title_element.inner_text().strip()
                print(f"  → First product title: {product_title[:50]}..." if len(product_title) > 50 else f"  → First product title: {product_title}")
        except:
            print(f"  ⚠ Could not extract product title")
        
        href = first_product.get_attribute("href")
        print(f"  ✓ Got href: {href}")
        
        if not href:
            raise Exception("Product link has no href attribute")
        
        # Construct full URL if needed
        if href.startswith("http"):
            product_url = href
        elif href.startswith("/"):
            product_url = f"https://donebydeer.com{href}"
        else:
            # If href is relative, construct from base URL
            product_url = f"https://donebydeer.com/{href}"
        
        print(f"  ✓ Product URL: {product_url}")
        return product_url
    
    def extract_product_data(self, page: Page, product_url: str) -> Product:
        """Extracts product data from Done by Deer product page."""
        print(f"  → Waiting for product title to be visible...")
        title_element = page.locator("h1.product-meta__title")
        title_element.wait_for(state="visible", timeout=15000)
        print(f"  ✓ Product title is visible")
        
        # Extract title
        print(f"  → Extracting product title...")
        title = title_element.inner_text().strip()
        print(f"  ✓ Title: {title[:50]}..." if len(title) > 50 else f"  ✓ Title: {title}")
        
        # Extract price
        print(f"  → Extracting product price...")
        price = ""
        price_element = page.locator(".price-list .price, .price--large").first
        if price_element.count() > 0:
            price = price_element.inner_text().strip()
            # Remove "Sale price" label if present
            price = price.replace("Sale price", "").strip()
            print(f"  ✓ Price: {price}")
        else:
            print(f"  ⚠ Price not found")
        
        # Extract SKU
        print(f"  → Extracting product SKU...")
        sku = ""
        sku_element = page.locator(".product-meta__sku-number")
        if sku_element.count() > 0:
            sku = sku_element.inner_text().strip()
            print(f"  ✓ SKU: {sku}")
        else:
            # Try alternative selector
            sku_wrapper = page.locator(".product-meta__sku")
            if sku_wrapper.count() > 0:
                sku_text = sku_wrapper.inner_text().strip()
                # Extract SKU number if there's a label
                if "varenr" in sku_text.lower() or "sku" in sku_text.lower():
                    # Try to extract the number part
                    parts = sku_text.split()
                    for part in parts:
                        if part.strip() and not part.lower() in ["varenr", "sku", ":", "."]:
                            sku = part.strip()
                            break
                else:
                    sku = sku_text
                if sku:
                    print(f"  ✓ SKU: {sku}")
                else:
                    print(f"  ⚠ SKU not found in expected format")
            else:
                print(f"  ⚠ SKU not found")
        
        # Extract description
        print(f"  → Extracting product description...")
        description = ""
        # Try to find description in the first tab (Description tab)
        # Look for the first visible tab content with description
        description_element = page.locator(".product-tabs__tab-item-content.rte").first
        if description_element.count() > 0:
            description = description_element.inner_text().strip()
            description = self.normalize_text(description)
            print(f"  ✓ Description length: {len(description)} characters")
        else:
            # Try alternative selector - look for collapsible content that's open
            description_element = page.locator("collapsible-content[open] .product-tabs__tab-item-content.rte, .product-tabs__tab-item-content").first
            if description_element.count() > 0:
                description = description_element.inner_text().strip()
                description = self.normalize_text(description)
                print(f"  ✓ Description length: {len(description)} characters")
            else:
                # Try to get all paragraphs from product tabs
                description_element = page.locator(".product-tabs__tab-item-content p, .product-content__tabs .rte p")
                if description_element.count() > 0:
                    # Combine all paragraphs
                    paragraphs = []
                    for i in range(description_element.count()):
                        para = description_element.nth(i).inner_text().strip()
                        if para:
                            paragraphs.append(para)
                    description = " ".join(paragraphs)
                    description = self.normalize_text(description)
                    print(f"  ✓ Description length: {len(description)} characters")
                else:
                    print(f"  ⚠ Description not found")
        
        # Extract images
        print(f"  → Extracting product images...")
        images = []
        seen_urls = set()
        
        # Try to find images in product media section
        image_elements = page.locator(".product__media-item img, .product__media-image-wrapper img").all()
        print(f"    Found {len(image_elements)} image element(s)")
        
        for img in image_elements:
            src = img.get_attribute("src")
            if not src:
                src = img.get_attribute("data-src")
            if src:
                clean_url = self.clean_image_url(src)
                if clean_url and clean_url not in seen_urls:
                    seen_urls.add(clean_url)
                    images.append(clean_url)
                    print(f"      Added image: {clean_url[:60]}...")
        
        # If no images found, try alternative selectors
        if not images:
            print(f"    → Trying alternative image selectors...")
            image_elements = page.locator("product-media img, .product__media img").all()
            print(f"    Found {len(image_elements)} image element(s)")
            
            for img in image_elements:
                src = img.get_attribute("src")
                if not src:
                    src = img.get_attribute("data-src")
                if src:
                    clean_url = self.clean_image_url(src)
                    if clean_url and clean_url not in seen_urls:
                        seen_urls.add(clean_url)
                        images.append(clean_url)
                        print(f"      Added image: {clean_url[:60]}...")
        
        print(f"  ✓ Found {len(images)} image(s)")
        
        # Set primary image as the first image (if images exist)
        primary_image = images[0] if images else ""
        
        # Extract specifications (if available)
        specifications = ""
        try:
            # Look for specifications in product tabs
            specs_element = page.locator(".product-tabs__tab-item-content").filter(has_text="material")
            if specs_element.count() > 0:
                specs_content = specs_element.first.inner_text().strip()
                specifications = self.normalize_text(specs_content)
        except:
            pass
        
        return Product(
            title=title,
            price=price,
            description=description,
            specifications=specifications,
            images=images,
            primary_image=primary_image,
            sku=sku,
            url=product_url
        )
