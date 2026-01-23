from playwright.sync_api import Page
import time
import json
import re
from scraper.base_scraper import BaseScraper
from scraper.models import Product


class LiewoodScraper(BaseScraper):
    """Scraper implementation for liewood.com"""
    
    def get_base_url(self) -> str:
        return "https://www.liewood.com"
    
    def perform_search(self, page: Page, search_text: str, navigation_delay: float = 0) -> None:
        """Performs search on LieWood website by navigating directly to search URL with product name."""
        print(f"  → Navigating to search URL with product name: '{search_text}'...")
        
        # Navigate directly to search URL with product name as query parameter
        search_url = f"{self.get_base_url()}/search?q={search_text}"
        page.goto(search_url, wait_until="load")
        
        if navigation_delay > 0:
            time.sleep(navigation_delay)
        
        # Wait for search results to load
        print(f"  → Waiting for search results to load...")
        
        # Wait for product search result panel specifically (not pages or articles)
        # The product panel has id="main-search-results-product"
        product_result_panel = page.locator('#main-search-results-product')
        product_result_panel.wait_for(state="visible", timeout=15000)
        print(f"  ✓ Product search results container is visible")
        
        # Wait for at least one product card to appear within the product panel
        product_cards = product_result_panel.locator("product-card, .product-card")
        try:
            product_cards.first.wait_for(state="visible", timeout=15000)
            print(f"  ✓ Product cards are visible")
        except Exception as e:
            print(f"  ⚠ No products found in search results: {str(e)}")
            raise Exception(f"No products found for product name: {search_text}")
    
    def get_first_product_link(self, page: Page, search_text: str) -> str:
        """Extracts the first product link from LieWood search results."""
        print(f"  → Looking for product links in search results...")
        
        # Wait for product search result panel specifically
        product_result_panel = page.locator('#main-search-results-product')
        product_result_panel.wait_for(state="visible", timeout=15000)
        
        # Wait for product list to be visible within the product panel
        product_list = product_result_panel.locator("product-list, .product-list")
        product_list.wait_for(state="visible", timeout=15000)
        
        # Find the first product card within the product panel
        first_product_card = product_result_panel.locator("product-card, .product-card").first
        first_product_card.wait_for(state="visible", timeout=15000)
        print(f"  ✓ Found first product card")
        
        # Try to find product link - check product-card__media link
        product_link = None
        
        # Try product-card__media link first
        media_link = first_product_card.locator("a.product-card__media, .product-card__media a").first
        if media_link.count() > 0:
            product_link = media_link
            print(f"  → Found product link via product-card__media")
        else:
            # Try product-title link as fallback
            title_link = first_product_card.locator("a.product-title, .product-title a").first
            if title_link.count() > 0:
                product_link = title_link
                print(f"  → Found product link via product-title")
        
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
        """Extracts product data from LieWood product page."""
        print(f"  → Extracting product data...")
        
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
        
        # Wait for product page to load
        print(f"  → Waiting for product page to load...")
        product_info = page.locator(".product-info, product-rerender").first
        product_info.wait_for(state="attached", timeout=15000)
        print(f"  ✓ Product page loaded")
        
        # Try to get product data from JSON script tag first (more reliable)
        product_json = None
        json_script = page.locator('script#product-json[type="application/json"]').first
        if json_script.count() > 0:
            try:
                json_text = json_script.inner_text()
                product_json = json.loads(json_text)
                print(f"  ✓ Found product JSON data")
            except Exception as e:
                print(f"  ⚠ Could not parse product JSON: {str(e)}")
        
        # Extract title
        print(f"  → Extracting product title...")
        title = ""
        
        # Try from JSON first
        if product_json and "title" in product_json:
            title = product_json["title"].strip()
            # Remove color variant from title if present (format: "Product Name - Color variant")
            if " - " in title:
                title = title.split(" - ")[0].strip()
            print(f"  ✓ Title from JSON: {title[:50]}..." if len(title) > 50 else f"  ✓ Title from JSON: {title}")
        
        # Fallback to HTML elements
        if not title:
            # Try ProductMeta__Title
            title_element = page.locator("h1.ProductMeta__Title, .ProductMeta__Title").first
            if title_element.count() > 0:
                title_text = title_element.inner_text().strip()
                # Extract just the product name (before color variant)
                if " - " in title_text:
                    title = title_text.split(" - ")[0].strip()
                else:
                    title = title_text
                print(f"  ✓ Title from ProductMeta__Title: {title[:50]}..." if len(title) > 50 else f"  ✓ Title: {title}")
        
        if not title:
            # Try product-title span
            title_span = page.locator("span.product-title.h6, .product-title").first
            if title_span.count() > 0:
                title = title_span.inner_text().strip()
                print(f"  ✓ Title from product-title span: {title[:50]}..." if len(title) > 50 else f"  ✓ Title: {title}")
        
        if not title:
            raise Exception("Product title not found")
        
        # Extract price
        print(f"  → Extracting product price...")
        price = ""
        price_element = page.locator("sale-price, .price-list sale-price").first
        if price_element.count() > 0:
            price_text = price_element.inner_text().strip()
            # Remove "Sale price" label if present
            price = re.sub(r"Sale price\s*", "", price_text, flags=re.IGNORECASE).strip()
            print(f"  ✓ Price: {price}")
        else:
            print(f"  ⚠ Price not found")
        
        # Extract SKU
        print(f"  → Extracting product SKU...")
        sku = ""
        
        # Try from JSON first
        if product_json and "variants" in product_json and len(product_json["variants"]) > 0:
            variant = product_json["variants"][0]
            if "sku" in variant:
                sku = variant["sku"].strip()
                print(f"  ✓ SKU from JSON: {sku}")
        
        # Fallback to HTML element
        if not sku:
            sku_element = page.locator("variant-sku, .variant-sku").first
            if sku_element.count() > 0:
                sku_text = sku_element.inner_text().strip()
                # Extract SKU from text like "SKU: LW14569\9883\ONE SIZE"
                if "SKU:" in sku_text:
                    sku = sku_text.split("SKU:")[1].strip()
                else:
                    sku = sku_text
                print(f"  ✓ SKU from variant-sku: {sku}")
        
        if not sku:
            print(f"  ⚠ SKU not found")
        
        # Extract description
        print(f"  → Extracting product description...")
        description = ""
        
        # Try to find and expand DESCRIPTION accordion if needed
        description_accordion = page.locator('accordion-disclosure:has(summary:has-text("DESCRIPTION"))').first
        if description_accordion.count() > 0:
            # Check if accordion is open
            details = description_accordion.locator("details").first
            if details.count() > 0:
                is_open = details.get_attribute("open")
                if not is_open:
                    # Try to expand using JavaScript to avoid cookie overlay blocking
                    try:
                        page.evaluate("""
                            (() => {
                                const accordion = document.querySelector('accordion-disclosure:has(summary:has-text("DESCRIPTION"))');
                                if (accordion) {
                                    const details = accordion.querySelector('details');
                                    if (details && !details.hasAttribute('open')) {
                                        details.setAttribute('open', '');
                                        return true;
                                    }
                                }
                                return false;
                            })();
                        """)
                        page.wait_for_timeout(500)
                        print(f"  → Expanded DESCRIPTION accordion via JavaScript")
                    except Exception as e:
                        print(f"  ⚠ Could not expand accordion via JavaScript: {str(e)}")
                        # Fallback: try clicking (may fail if overlay is still blocking)
                        try:
                            summary = details.locator("summary").first
                            if summary.count() > 0:
                                summary.click(timeout=5000)
                                page.wait_for_timeout(500)
                                print(f"  → Expanded DESCRIPTION accordion via click")
                        except Exception as e2:
                            print(f"  ⚠ Could not expand accordion via click: {str(e2)}")
            
            # Extract description text
            description_element = description_accordion.locator(".accordion__content.prose, .accordion__content").first
            if description_element.count() > 0:
                description = description_element.inner_text().strip()
                description = self.normalize_text(description)
                print(f"  ✓ Description length: {len(description)} characters")
        
        # If no description from accordion, try from JSON
        if not description and product_json and "description" in product_json:
            description = product_json["description"].strip()
            # Remove HTML tags if present
            description = re.sub(r"<[^>]+>", "", description)
            description = self.normalize_text(description)
            print(f"  ✓ Description from JSON, length: {len(description)} characters")
        
        if not description:
            print(f"  ⚠ Description not found")
        
        # Extract specifications
        print(f"  → Extracting product specifications...")
        specifications = ""
        
        # LieWood website does not have a separate specifications section
        # All product information is in the description
        # Return empty specifications to avoid extracting footer/legal text
        print(f"  ✓ No specifications section available (information is in description)")
        
        # Extract images
        print(f"  → Extracting product images...")
        images = []
        seen_urls = set()
        
        # Try from JSON first (more reliable)
        if product_json and "images" in product_json:
            for image_url in product_json["images"]:
                if image_url:
                    clean_url = self.clean_image_url(image_url)
                    if clean_url and clean_url not in seen_urls:
                        seen_urls.add(clean_url)
                        images.append(clean_url)
                        print(f"      Added image from JSON: {clean_url[:60]}...")
        
        # Fallback to HTML elements
        if not images:
            # Extract from product gallery images
            image_elements = page.locator("product-gallery img, .product-gallery img, .product-gallery__media img").all()
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
