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
        
        # Wait for search result panel to appear (element-based wait)
        search_panel = page.locator("search-result-panel#main-search-results-product")
        search_panel.wait_for(state="visible", timeout=15000)
        
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
        search_panel = page.locator("search-result-panel#main-search-results-product")
        search_panel.wait_for(state="visible", timeout=20000)
        
        # Wait for product list to appear
        product_list = page.locator("product-list")
        product_list.wait_for(state="visible", timeout=15000)
        
        # Wait for product cards to appear
        product_card = page.locator("product-card.product-card").first
        product_card.wait_for(state="visible", timeout=10000)
        
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
        
        # Find the product link
        product_link = product_card.locator(".product-card__media a").first
        product_link.wait_for(state="attached", timeout=5000)
        href = product_link.get_attribute("href")
        
        if not href:
            raise Exception("Product link has no href attribute")
        
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
        if not product_json or "title" not in product_json:
            raise Exception("Product JSON not found or missing title")
        title = product_json["title"]
        
        # Extract price
        if not product_json or "price" not in product_json:
            raise Exception("Product JSON not found or missing price")
        # Price is in cents, convert to euros
        price_cents = product_json["price"]
        price = f"€{price_cents / 100:.2f}"
        
        # Extract description
        if not product_json:
            raise Exception("Product JSON not found")
        description = ""
        # Try description field first
        if "description" in product_json:
            description = product_json["description"]
        elif "content" in product_json:
            description = product_json["content"]
        
        # Strip HTML tags from JSON description (JSON contains HTML)
        if description:
            soup = BeautifulSoup(description, 'html.parser')
            description = soup.get_text(separator=' ', strip=True)
        
        # Normalize description
        description = self.normalize_text(description)
        
        # Extract SKU
        if not product_json or "variants" not in product_json or len(product_json["variants"]) == 0:
            raise Exception("Product JSON not found or missing variants")
        sku = product_json["variants"][0].get("sku", "")
        
        # Extract images
        images = []
        seen_urls = set()
        
        if not product_json or "images" not in product_json:
            raise Exception("Product JSON not found or missing images")
        # Extract from JSON
        for img_url in product_json["images"]:
            clean_url = self.clean_image_url(img_url)
            if clean_url and clean_url not in seen_urls:
                seen_urls.add(clean_url)
                images.append(clean_url)
        
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
