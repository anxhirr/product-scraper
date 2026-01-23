from playwright.sync_api import Page
import time
import re
from scraper.base_scraper import BaseScraper
from scraper.models import Product
from scraper.services.cookie_consent_service import CookieConsentService


class WookidsScraper(BaseScraper):
    """Scraper implementation for wookids.eu"""
    
    def get_base_url(self) -> str:
        return "https://wookids.eu"
    
    def perform_search(self, page: Page, search_text: str, navigation_delay: float = 0) -> None:
        """Performs search on Wookids website by navigating directly to search URL with product code."""
        print(f"  → Transforming product code: '{search_text}'...")
        
        # Transform product code: remove "WK" prefix if present (case-insensitive)
        product_code = search_text.strip()
        if product_code.upper().startswith("WK"):
            product_code = product_code[2:].strip()
            print(f"  ✓ Removed 'WK' prefix, using code: '{product_code}'")
        else:
            print(f"  ✓ Using code as-is: '{product_code}'")
        
        # Navigate directly to search URL with product code as query parameter
        search_url = f"{self.get_base_url()}/en/search?query={product_code}"
        print(f"  → Navigating to search URL: '{search_url}'...")
        page.goto(search_url, wait_until="load")
        
        if navigation_delay > 0:
            time.sleep(navigation_delay)
        
        # Wait for search results to load
        print(f"  → Waiting for search results to load...")
        
        # Wait for search container
        search_container = page.locator('#searchkit-faceting-container')
        search_container.wait_for(state="visible", timeout=15000)
        print(f"  ✓ Search container is visible")
        
        # Wait for product grid
        product_grid = page.locator('.euiFlexGrid.products-wrapper')
        try:
            product_grid.wait_for(state="visible", timeout=15000)
            print(f"  ✓ Product grid is visible")
        except Exception as e:
            print(f"  ⚠ Product grid may not be visible: {str(e)}")
        
        # Wait for at least one product thumbnail to appear
        product_thumbnails = page.locator('.product-thumbnail')
        try:
            product_thumbnails.first.wait_for(state="visible", timeout=15000)
            print(f"  ✓ Product thumbnails are visible")
        except Exception as e:
            print(f"  ⚠ No products found in search results: {str(e)}")
            raise Exception(f"No products found for product code: {product_code}")
    
    def get_first_product_link(self, page: Page, search_text: str) -> str:
        """Extracts the first product link from Wookids search results."""
        print(f"  → Looking for product links in search results...")
        
        # Wait for product grid to be visible
        product_grid = page.locator('.euiFlexGrid.products-wrapper')
        product_grid.wait_for(state="visible", timeout=15000)
        
        # Find the first product thumbnail
        first_product = page.locator('.product-thumbnail').first
        first_product.wait_for(state="visible", timeout=15000)
        print(f"  ✓ Found first product thumbnail")
        
        # Try to find product link - check lnk-product first, then euiLink
        product_link = None
        
        # Try lnk-product link first
        lnk_product = first_product.locator('a.lnk-product').first
        if lnk_product.count() > 0:
            product_link = lnk_product
            print(f"  → Found product link via lnk-product")
        else:
            # Try euiLink as fallback
            eui_link = first_product.locator('a.euiLink').first
            if eui_link.count() > 0:
                product_link = eui_link
                print(f"  → Found product link via euiLink")
        
        if not product_link or product_link.count() == 0:
            raise Exception("No product link found in search results")
        
        # Extract href attribute
        href = product_link.get_attribute("href")
        print(f"  ✓ Got href: {href}")
        
        if not href:
            raise Exception("Product link has no href attribute")
        
        # Construct full URL if needed
        if href.startswith("http"):
            product_url = href
        elif href.startswith("/"):
            product_url = f"{self.get_base_url()}{href}"
        else:
            product_url = f"{self.get_base_url()}/{href}"
        
        print(f"  ✓ Product URL: {product_url}")
        return product_url
    
    def extract_product_data(self, page: Page, product_url: str) -> Product:
        """Extracts product data from Wookids product page."""
        print(f"  → Extracting product data...")
        
        # Handle cookie consent overlay if present
        CookieConsentService.handle(page)
        
        # Wait for product page to load
        print(f"  → Waiting for product page to load...")
        product_info = page.locator('#product-info').first
        product_info.wait_for(state="attached", timeout=15000)
        print(f"  ✓ Product page loaded")
        
        # Extract title
        print(f"  → Extracting product title...")
        title = ""
        title_element = page.locator('h1.product-model-name').first
        if title_element.count() > 0:
            title = title_element.inner_text().strip()
            print(f"  ✓ Title: {title[:50]}..." if len(title) > 50 else f"  ✓ Title: {title}")
        else:
            raise Exception("Product title not found")
        
        # Extract SKU
        print(f"  → Extracting product SKU...")
        sku = ""
        sku_element = page.locator('.price-sku').first
        if sku_element.count() > 0:
            sku_text = sku_element.inner_text().strip()
            # Extract SKU from text like "sku: 30175559"
            if "sku:" in sku_text.lower():
                sku = sku_text.split(":")[-1].strip()
            else:
                sku = sku_text
            print(f"  ✓ SKU: {sku}")
        else:
            print(f"  ⚠ SKU not found")
        
        # Extract price
        print(f"  → Extracting product price...")
        price = ""
        # Try EUR currency format first
        price_element = page.locator('.currency-format[data-currency="EUR"]').first
        if price_element.count() > 0:
            price = price_element.inner_text().strip()
            print(f"  ✓ Price from EUR format: {price}")
        else:
            # Fallback to price_value
            price_value_element = page.locator('.price_value').first
            if price_value_element.count() > 0:
                price = price_value_element.inner_text().strip()
                print(f"  ✓ Price from price_value: {price}")
            else:
                print(f"  ⚠ Price not found")
        
        # Extract description
        print(f"  → Extracting product description...")
        description = ""
        
        # Try to find and expand DESCRIPTION accordion if needed
        description_accordion = page.locator('#description').first
        if description_accordion.count() > 0:
            # Always try to expand using JavaScript (more reliable)
            try:
                page.evaluate("""
                    (() => {
                        const accordion = document.querySelector('#description');
                        if (accordion) {
                            // Remove collapse class and add show class
                            accordion.classList.remove('collapse');
                            accordion.classList.add('show');
                            // Also set inline styles to ensure visibility
                            accordion.style.display = 'block';
                            accordion.style.height = 'auto';
                            return true;
                        }
                        return false;
                    })();
                """)
                page.wait_for_timeout(1000)  # Wait longer for content to be accessible
                print(f"  → Expanded DESCRIPTION accordion via JavaScript")
            except Exception as e:
                print(f"  ⚠ Could not expand accordion via JavaScript: {str(e)}")
                # Fallback: try clicking the toggle
                try:
                    toggle = page.locator('a[data-target="#description"], a[aria-controls="description"]').first
                    if toggle.count() > 0:
                        toggle.click(timeout=5000)
                        page.wait_for_timeout(1000)
                        print(f"  → Expanded DESCRIPTION accordion via click")
                except Exception as e2:
                    print(f"  ⚠ Could not expand accordion via click: {str(e2)}")
            
            # Extract description text - try multiple approaches
            # First, try to get text directly from #description
            try:
                description_text = description_accordion.inner_text().strip()
                if description_text:
                    description = self.normalize_text(description_text)
                    print(f"  ✓ Description length: {len(description)} characters")
            except Exception as e:
                print(f"  ⚠ Could not extract description from accordion: {str(e)}")
            
            # If that didn't work, try using JavaScript to extract HTML content
            if not description:
                try:
                    description_html = page.evaluate("""
                        (() => {
                            const accordion = document.querySelector('#description');
                            if (accordion) {
                                // Get all text content, preserving structure
                                return accordion.innerText || accordion.textContent || '';
                            }
                            return '';
                        })();
                    """)
                    if description_html:
                        description = self.normalize_text(description_html.strip())
                        print(f"  ✓ Description extracted via JavaScript, length: {len(description)} characters")
                except Exception as e:
                    print(f"  ⚠ Could not extract description via JavaScript: {str(e)}")
        
        if not description:
            print(f"  ⚠ Description not found")
        
        # Extract specifications
        print(f"  → Extracting product specifications...")
        specifications = ""
        
        # Try to find and expand CARACTERISTICS accordion (note: typo in HTML)
        caracteristics_accordion = page.locator('#caracteristics').first
        if caracteristics_accordion.count() > 0:
            # Check if accordion is open
            is_collapsed = caracteristics_accordion.get_attribute("class")
            if is_collapsed and "collapse" in is_collapsed and "show" not in is_collapsed:
                # Try to expand using JavaScript
                try:
                    page.evaluate("""
                        (() => {
                            const accordion = document.querySelector('#caracteristics');
                            if (accordion && accordion.classList.contains('collapse')) {
                                accordion.classList.add('show');
                                return true;
                            }
                            return false;
                        })();
                    """)
                    page.wait_for_timeout(500)
                    print(f"  → Expanded CARACTERISTICS accordion via JavaScript")
                except Exception as e:
                    print(f"  ⚠ Could not expand accordion via JavaScript: {str(e)}")
                    # Fallback: try clicking the toggle
                    try:
                        toggle = page.locator('a[data-target="#caracteristics"]').first
                        if toggle.count() > 0:
                            toggle.click(timeout=5000)
                            page.wait_for_timeout(500)
                            print(f"  → Expanded CARACTERISTICS accordion via click")
                    except Exception as e2:
                        print(f"  ⚠ Could not expand accordion via click: {str(e2)}")
            
            # Extract specifications from table
            specs_table = caracteristics_accordion.locator('table').first
            if specs_table.count() > 0:
                spec_lines = []
                # Extract table rows
                rows = specs_table.locator('tbody tr').all()
                for row in rows:
                    th = row.locator('th').first
                    td = row.locator('td').first
                    if th.count() > 0 and td.count() > 0:
                        key = th.inner_text().strip()
                        value = td.inner_text().strip()
                        if key and value:
                            spec_lines.append(f"{key}: {value}")
                
                if spec_lines:
                    specifications = "\n".join(spec_lines)
                    print(f"  ✓ Extracted {len(spec_lines)} specification(s)")
        
        if not specifications:
            print(f"  ⚠ No specifications found")
        
        # Extract images
        print(f"  → Extracting product images...")
        images = []
        seen_urls = set()
        
        # Try to find images in carousel
        image_elements = page.locator('.carousel-item img, .product-attr.product-image img').all()
        print(f"    Found {len(image_elements)} image element(s)")
        
        for img in image_elements:
            # Try data-src first (lazy loading), then src
            src = img.get_attribute("data-src")
            if not src:
                src = img.get_attribute("src")
            
            if src:
                clean_url = self.clean_image_url(src)
                if clean_url and clean_url not in seen_urls:
                    seen_urls.add(clean_url)
                    images.append(clean_url)
                    print(f"      Added image: {clean_url[:60]}...")
        
        # If no images from carousel, try other image selectors
        if not images:
            image_elements = page.locator('.product-image img, img[data-src], img[src]').all()
            print(f"    Trying alternative selectors, found {len(image_elements)} image element(s)")
            
            for img in image_elements:
                src = img.get_attribute("data-src")
                if not src:
                    src = img.get_attribute("src")
                
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
            specifications=specifications,
            images=images,
            primary_image=primary_image,
            sku=sku,
            url=product_url
        )
