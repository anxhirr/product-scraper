from playwright.sync_api import Page
from urllib.parse import quote_plus
import json
import time
from bs4 import BeautifulSoup
from scraper.base_scraper import BaseScraper
from scraper.models import Product


class LiewoodScraper(BaseScraper):
    """Scraper implementation for liewood.com"""
    
    def get_base_url(self) -> str:
        return "https://www.liewood.com/"
    
    def perform_search(self, page: Page, search_text: str, navigation_delay: float = 0) -> None:
        """Performs search on Liewood website by navigating to search URL."""
        print(f"  Searching for '{search_text}'...")
        
        # URL-encode the search text
        encoded_query = quote_plus(search_text)
        search_url = f"https://www.liewood.com/search?q={encoded_query}"
        
        # Navigate to search results page - use "load" instead of "networkidle" 
        # as the page may have continuous network activity
        page.goto(search_url, wait_until="load", timeout=30000)
        
        # Add delay after navigation if specified
        if navigation_delay > 0:
            time.sleep(navigation_delay)
        
        # Wait for the page to be ready
        page.wait_for_load_state("domcontentloaded")
        
        # Wait for search result panel or product list to appear (element-based wait)
        # This replaces the fixed 5000ms timeout with a more efficient element-based wait
        try:
            # Try waiting for search-result-panel first (more specific)
            search_panel = page.locator("search-result-panel#main-search-results-product, search-result-panel")
            search_panel.first.wait_for(state="visible", timeout=15000)
        except Exception:
            # Fallback to product-list
            try:
                product_list = page.locator("product-list")
                product_list.wait_for(state="visible", timeout=15000)
            except Exception:
                pass  # Continue even if elements not found immediately
        
        # Wait for network to be idle (search results might be loading via API calls)
        # Reduced timeout since we already waited for elements
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except:
            pass  # Continue even if networkidle times out
        
        print(f"  ✓ Search completed")
    
    def get_first_product_link(self, page: Page, search_text: str) -> str:
        """Extracts the first product link from Liewood search results."""
        # Wait for search result panel to load first
        try:
            search_panel = page.locator("search-result-panel#main-search-results-product")
            search_panel.wait_for(state="visible", timeout=20000)
        except Exception:
            # Try without ID
            search_panel = page.locator("search-result-panel")
            try:
                search_panel.first.wait_for(state="visible", timeout=15000)
            except Exception:
                pass
        
        # Wait for product list to appear
        try:
            product_list = page.locator("product-list")
            product_list.wait_for(state="visible", timeout=15000)
        except Exception:
            pass
        
        # Wait for product cards to appear - try multiple selectors
        product_card = None
        card_selectors = [
            "product-card.product-card",
            "product-card",
            ".product-list product-card",
            "product-list product-card"
        ]
        
        for selector in card_selectors:
            try:
                cards = page.locator(selector)
                if cards.count() > 0:
                    product_card = cards.first
                    product_card.wait_for(state="visible", timeout=10000)
                    if cards.count() > 0:
                        break
            except Exception:
                continue
        
        # If still no cards found, try one more time with a brief wait
        if product_card is None:
            try:
                all_cards = page.locator("product-card")
                all_cards.first.wait_for(state="visible", timeout=5000)
                if all_cards.count() > 0:
                    product_card = all_cards.first
            except Exception:
                pass
        
        # Consolidated "no results" check - only check once after waiting for cards
        # Cache page text to avoid multiple calls
        if product_card is None:
            page_text = page.locator("body").inner_text()
            has_no_results = (
                "0 result" in page_text.lower() or 
                "no result" in page_text.lower() or
                "did not yield any result" in page_text.lower() or
                "your search did not yield" in page_text.lower()
            )
            
            # If we see "no results", wait briefly and re-check once
            if has_no_results:
                page.wait_for_timeout(1000)  # Reduced from 3000ms
                # Re-check after brief wait
                page_text = page.locator("body").inner_text()
                has_no_results = (
                    "0 result" in page_text.lower() or 
                    "no result" in page_text.lower() or
                    "did not yield any result" in page_text.lower() or
                    "your search did not yield" in page_text.lower()
                )
            
            # If search has no results, fail immediately - don't use popular products
            if has_no_results:
                raise Exception(f"No products found for search: '{search_text}'. The search returned no results.")
            
            # Final check - verify no results message
            if "0 result" in page_text.lower() or "no result" in page_text.lower():
                raise Exception(f"No products found for search: '{search_text}'")
            raise Exception(f"No product cards found in search results. Page may still be loading or search returned no results.")
        
        # Find the product link - try multiple selectors
        link_selectors = [
            ".product-card__media a",
            "a.product-card__media",
            ".product-title a",
            "a[href*='/products/']"
        ]
        
        product_link = None
        for selector in link_selectors:
            link_elements = product_card.locator(selector)
            if link_elements.count() > 0:
                product_link = link_elements.first
                # Wait for the link to be ready
                try:
                    product_link.wait_for(state="attached", timeout=5000)
                except Exception:
                    pass
                break
        
        if product_link is None:
            raise Exception("Could not find product link in first product card")
        
        # Wait for the link to have an href attribute (might be set dynamically)
        # Use element-based wait: wait for element to be attached, then check href
        # If href is not immediately available, use a brief efficient wait
        product_link.wait_for(state="attached", timeout=5000)
        href = product_link.get_attribute("href")
        
        # If href is still not available, wait briefly and check again (max 2 attempts)
        if not href:
            page.wait_for_timeout(500)  # Brief wait for dynamic content
            href = product_link.get_attribute("href")
        
        if not href:
            raise Exception("Product link has no href attribute after waiting")
        
        # Handle relative URLs
        if href.startswith("http"):
            product_url = href
        elif href.startswith("/"):
            product_url = f"https://www.liewood.com{href}"
        else:
            product_url = f"https://www.liewood.com/{href}"
        
        return product_url
    
    def extract_product_data(self, page: Page, product_url: str) -> Product:
        """Extracts product data from Liewood product page."""
        print(f"  Extracting product data...")
        
        # Wait for page to load
        page.wait_for_load_state("load")
        
        # Try to extract from JSON script tag first (more reliable)
        product_json = None
        try:
            json_script = page.locator("#product-json")
            if json_script.count() > 0:
                json_text = json_script.inner_text()
                product_json = json.loads(json_text)
        except Exception:
            pass
        
        # Extract title
        title = ""
        if product_json and "title" in product_json:
            title = product_json["title"]
        else:
            # Try HTML selectors
            title_selectors = [
                "h1.ProductMeta__Title .product-title",
                ".product-title",
                "h1.ProductMeta__Title",
                "h1"
            ]
            for selector in title_selectors:
                title_el = page.locator(selector).first
                if title_el.count() > 0:
                    title = title_el.inner_text().strip()
                    if title:
                        break
        
        if not title:
            raise Exception("Could not find product title")
        
        # Extract price
        price = ""
        if product_json and "price" in product_json:
            # Price is in cents, convert to euros
            price_cents = product_json["price"]
            price = f"€{price_cents / 100:.2f}"
        else:
            # Try HTML selectors
            price_selectors = [
                "sale-price",
                ".sale-price",
                "price-list sale-price",
                ".price-list .sale-price"
            ]
            for selector in price_selectors:
                price_el = page.locator(selector).first
                if price_el.count() > 0:
                    price_text = price_el.inner_text().strip()
                    # Remove "Sale price" label if present
                    price = price_text.replace("Sale price", "").strip()
                    if price:
                        break
        
        if not price:
            price = "Price not available"
        
        # Extract description
        description = ""
        if product_json:
            # Try description field first
            if "description" in product_json:
                description = product_json["description"]
            elif "content" in product_json:
                description = product_json["content"]
            
            # Strip HTML tags from JSON description (JSON contains HTML)
            if description:
                soup = BeautifulSoup(description, 'html.parser')
                description = soup.get_text(separator=' ', strip=True)
        
        # Also try to get from accordion
        if not description:
            try:
                # Find accordion with "DESCRIPTION" in summary
                description_accordion = page.locator("accordion-disclosure").filter(has_text="DESCRIPTION")
                if description_accordion.count() > 0:
                    # Get the content from accordion (already plain text from inner_text)
                    accordion_content = description_accordion.first.locator(".accordion__content")
                    if accordion_content.count() > 0:
                        description = accordion_content.first.inner_text().strip()
            except Exception:
                pass
        
        # Normalize description
        description = self.normalize_text(description)
        
        # Extract SKU
        sku = ""
        if product_json and "variants" in product_json and len(product_json["variants"]) > 0:
            sku = product_json["variants"][0].get("sku", "")
        else:
            # Try HTML selector
            sku_el = page.locator(".variant-sku, variant-sku")
            if sku_el.count() > 0:
                sku_text = sku_el.first.inner_text().strip()
                # Remove "SKU:" label if present
                sku = sku_text.replace("SKU:", "").strip()
        
        if not sku:
            sku = ""
        
        # Extract images
        images = []
        seen_urls = set()
        
        if product_json and "images" in product_json:
            # Extract from JSON
            for img_url in product_json["images"]:
                clean_url = self.clean_image_url(img_url)
                if clean_url and clean_url not in seen_urls:
                    seen_urls.add(clean_url)
                    images.append(clean_url)
        
        # Also try to get from HTML gallery
        if not images:
            try:
                image_elements = page.locator(".product-gallery__media img, product-gallery__media img")
                image_count = image_elements.count()
                
                for i in range(image_count):
                    img = image_elements.nth(i)
                    src = img.get_attribute("src")
                    if not src:
                        src = img.get_attribute("data-src")
                    if src:
                        clean_url = self.clean_image_url(src)
                        if clean_url and clean_url not in seen_urls:
                            seen_urls.add(clean_url)
                            images.append(clean_url)
            except Exception:
                pass
        
        # Set primary image as the first image (if images exist)
        primary_image = images[0] if images else ""
        
        # Extract specifications (if available)
        specifications = ""
        try:
            # Find specifications in the DESCRIPTION accordion ONLY
            # Specifications are in a span with class "metafield-multi_line_text_field"
            # The structure is: accordion-disclosure > details > summary > div.accordion__content > p > span.metafield-multi_line_text_field
            
            # Find all summary elements and check which one contains "DESCRIPTION"
            all_summaries = page.locator("summary.accordion__summary")
            summary_count = all_summaries.count()
            
            description_accordion = None
            for i in range(summary_count):
                summary = all_summaries.nth(i)
                summary_text = summary.inner_text().strip()
                
                # Check if this summary contains "DESCRIPTION" (case-insensitive)
                if "DESCRIPTION" in summary_text.upper():
                    # Get the parent accordion-disclosure element (custom element wrapper)
                    accordion_wrapper = summary.locator("xpath=ancestor::accordion-disclosure")
                    if accordion_wrapper.count() > 0:
                        description_accordion = accordion_wrapper.first
                        break
            
            if description_accordion:
                # Look for the metafield span within the accordion content div
                # The span is inside: details > div.accordion__content > p > span
                metafield_span = description_accordion.locator("details .accordion__content span.metafield-multi_line_text_field")
                
                # If not found, try without the details selector
                if metafield_span.count() == 0:
                    metafield_span = description_accordion.locator(".accordion__content span.metafield-multi_line_text_field")
                
                if metafield_span.count() > 0:
                    span_element = metafield_span.first
                    # Use text_content() since inner_text() returns null for non-visible elements
                    # text_content() works regardless of visibility
                    text_content = span_element.text_content()
                    spec_text = text_content.strip() if text_content else ""
                    
                    if spec_text:
                        # Specifications can be separated by periods or semicolons
                        # Try semicolon first (more common), then period
                        if ";" in spec_text:
                            spec_parts = [s.strip() for s in spec_text.split(";") if s.strip()]
                        else:
                            spec_parts = [s.strip() for s in spec_text.split(".") if s.strip()]
                        specifications = "\n".join(spec_parts)
        except Exception:
            pass
        
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
