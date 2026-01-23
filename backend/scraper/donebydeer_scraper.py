from playwright.sync_api import Page
import time
import re
from scraper.base_scraper import BaseScraper
from scraper.models import Product


class DoneByDeerScraper(BaseScraper):
    """Scraper implementation for donebydeer.com"""
    
    def get_base_url(self) -> str:
        return "https://donebydeer.com/en-gb"
    
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
                print(f"  → Cookie overlay detected, dismissing...")
            except Exception as e:
                print(f"  ⚠ Cookie overlay handling failed: {str(e)}")
            finally:
                # Force hide overlay programmatically (this is the only method that actually works)
                try:
                    page.evaluate("""
                        document.querySelectorAll('#coiOverlay, .coiOverlay-container, #cookie-information-template-wrapper').forEach(el => {
                            el.setAttribute('aria-hidden', 'true');
                            el.style.display = 'none';
                            el.style.pointerEvents = 'none';
                            el.style.zIndex = '-1';
                        });
                    """)
                    page.wait_for_timeout(500)
                    print(f"  ✓ Hid cookie overlay programmatically")
                except:
                    pass
        
        print(f"  → Looking for search button...")
        
        # Find the search button/link in the header
        # The desktop search button is in .header__secondary-links
        search_button = page.locator('.header__secondary-links a[href*="/search"]').first
        search_button.wait_for(state="visible", timeout=5000)
        print(f"  ✓ Found desktop search button")
        
        print(f"  → Clicking search button to open drawer...")
        # Ensure button is actionable before clicking
        search_button.wait_for(state="visible", timeout=5000)
        search_button.click(timeout=10000)
        print(f"  ✓ Clicked search button")
        
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
            # href already includes /en-gb if it's a full path
            product_url = f"https://donebydeer.com{href}"
        else:
            # If href is relative, construct from base URL
            product_url = f"https://donebydeer.com/en-gb/{href}"
        
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
        
        print(f"  ✓ Found {len(images)} image(s)")
        
        # Set primary image as the first image (if images exist)
        primary_image = images[0] if images else ""
        
        # Extract specifications (if available)
        specifications = ""
        specs_dict = {}
        
        def extract_specs_from_html(content_element) -> dict:
            """Extract key-value pairs from HTML structure using <strong> tags as keys."""
            result = {}
            try:
                # Use JavaScript to extract key-value pairs from the HTML structure
                # Keys are in <strong> tags, values are text nodes after them
                html_content = content_element.evaluate("""
                    (element) => {
                        const result = {};
                        const strongTags = element.querySelectorAll('strong');
                        
                        strongTags.forEach((strong, index) => {
                            // Skip if parent has product-meta__sku class (SKU section)
                            const parent = strong.parentElement;
                            if (parent && parent.classList.contains('product-meta__sku')) {
                                return;
                            }
                            
                            const keyText = strong.textContent.trim();
                            
                            // Check if this looks like a key (ends with colon)
                            if (keyText.endsWith(':')) {
                                const key = keyText.slice(0, -1).trim();
                                
                                // Get value - collect text nodes after this strong tag until next strong
                                const valueParts = [];
                                let node = strong.nextSibling;
                                
                                while (node) {
                                    if (node.nodeType === 3) { // Text node
                                        const text = node.textContent.trim();
                                        if (text) {
                                            valueParts.push(text);
                                        }
                                    } else if (node.nodeType === 1) { // Element node
                                        if (node.tagName === 'STRONG' || node.tagName === 'strong') {
                                            break; // Stop at next strong tag
                                        }
                                        // Get text content but skip if it contains nested strong tags
                                        if (!node.querySelector('strong')) {
                                            const text = node.textContent.trim();
                                            if (text) {
                                                valueParts.push(text);
                                            }
                                        }
                                    }
                                    node = node.nextSibling;
                                }
                                
                                const value = valueParts.join(' ').trim();
                                if (value) {
                                    result[key] = value;
                                }
                            }
                        });
                        
                        return result;
                    }
                """)
                
                result = html_content
            except Exception as e:
                print(f"    ⚠ Error parsing HTML structure: {str(e)}")
            
            return result
        
        try:
            # Extract "Good to know" section
            print(f"  → Extracting 'Good to know' section...")
            good_to_know_content = None
            
            # Find the tab button with "Good to know" text and get its aria-controls
            good_to_know_button = page.locator("button.tabs-nav__item, button.collapsible-toggle").filter(has_text="Good to know").first
            if good_to_know_button.count() > 0:
                aria_controls = good_to_know_button.get_attribute("aria-controls")
                if aria_controls:
                    good_to_know_content = page.locator(f"#{aria_controls} .product-tabs__tab-item-content.rte, #{aria_controls} .product-tabs__tab-item-content").first
                    if good_to_know_content.count() > 0:
                        print(f"  ✓ Found 'Good to know' content via aria-controls")
            
            # Extract key-value pairs from HTML structure
            if good_to_know_content and good_to_know_content.count() > 0:
                parsed = extract_specs_from_html(good_to_know_content)
                specs_dict.update(parsed)
                print(f"  ✓ Extracted {len(parsed)} key-value pair(s) from 'Good to know'")
        except Exception as e:
            print(f"  ⚠ Error extracting 'Good to know': {str(e)}")
        
        try:
            # Extract Material section (if available)
            print(f"  → Extracting 'Material' section...")
            material_content = None
            
            # Find the tab button with "Material" text and get its aria-controls
            material_button = page.locator("button.tabs-nav__item, button.collapsible-toggle").filter(has_text="Material").first
            if material_button.count() > 0:
                aria_controls = material_button.get_attribute("aria-controls")
                if aria_controls:
                    material_content = page.locator(f"#{aria_controls} .product-tabs__tab-item-content.rte, #{aria_controls} .product-tabs__tab-item-content").first
                    if material_content.count() > 0:
                        print(f"  ✓ Found 'Material' content via aria-controls")
            
            # Extract key-value pairs from Material HTML structure
            if material_content and material_content.count() > 0:
                material_parsed = extract_specs_from_html(material_content)
                specs_dict.update(material_parsed)
                print(f"  ✓ Extracted {len(material_parsed)} key-value pair(s) from Material section")
        except Exception as e:
            print(f"  ⚠ Error extracting 'Material': {str(e)}")
        
        # Format specifications as key-value pairs separated by newlines
        # Format: "Key: Value\nKey2: Value2"
        if specs_dict:
            specs_lines = []
            for key, value in specs_dict.items():
                # Normalize the value
                value = self.normalize_text(value)
                # Remove "Find more info on our materials here" text and variations
                value = re.sub(r'\s*Find more info on our materials here\s*\([^)]*\)\.?\s*', '', value, flags=re.IGNORECASE)
                value = value.strip()
                # Format as "Key: Value"
                specs_lines.append(f"{key}: {value}")
            specifications = "\n".join(specs_lines)
            print(f"  ✓ Formatted {len(specs_dict)} specification(s)")
        else:
            print(f"  ⚠ No specifications found")
        
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
