from playwright.sync_api import Page
from scraper.base_scraper import BaseScraper
from scraper.models import Product


class HapeScraper(BaseScraper):
    """Scraper implementation for toys.hape.com"""
    
    def get_base_url(self) -> str:
        return "https://toys.hape.com/"
    
    def perform_search(self, page: Page, search_text: str) -> None:
        """Performs search on Hape website."""
        print(f"  → Looking for search input...")
        search_input = page.locator("input[type='search']")
        print(f"  ✓ Found search input")
        print(f"  → Filling search input with: '{search_text}'...")
        search_input.fill(search_text)
        print(f"  ✓ Filled search input")
        print(f"  → Pressing Enter to submit search...")
        search_input.press("Enter")
        print(f"  ✓ Search submitted")
    
    def get_first_product_link(self, page: Page, search_text: str) -> str:
        """Extracts the first product link from Hape search results."""
        print(f"  → Looking for product links in search results...")
        first_product = page.locator('a[href*="/products/"]').first
        print(f"  → Waiting for first product link to be visible...")
        first_product.wait_for(state="visible", timeout=15000)
        print(f"  ✓ Product link is visible")
        print(f"  → Extracting href attribute...")
        href = first_product.get_attribute("href")
        print(f"  ✓ Got href: {href}")
        product_url = f"https://toys.hape.com{href}"
        print(f"  ✓ Product URL: {product_url}")
        return product_url
    
    def extract_product_data(self, page: Page, product_url: str) -> Product:
        """Extracts product data from Hape product page."""
        print(f"  → Waiting for product title to be visible...")
        title_element = page.locator("h1.product-detail__title")
        title_element.wait_for(state="visible", timeout=15000)
        print(f"  ✓ Product title is visible")
        
        # Extract title
        print(f"  → Extracting product title...")
        title = page.locator("h1.product-detail__title").inner_text().strip()
        print(f"  ✓ Title: {title[:50]}..." if len(title) > 50 else f"  ✓ Title: {title}")
        
        # Extract price - use first if multiple prices exist
        print(f"  → Extracting product price...")
        price = page.locator("span.price.price-same-style.heading-style").first.inner_text().strip()
        print(f"  ✓ Price: {price}")
        
        # Extract description from collapsible-block with "Description" heading
        print(f"  → Extracting product description...")
        description = ""
        specifications = ""
        description_blocks = page.locator("collapsible-block").all()
        print(f"    Found {len(description_blocks)} collapsible block(s)")
        for block in description_blocks:
            heading = block.locator("h3.collapsible-heading").inner_text().strip()
            print(f"    Checking block with heading: {heading}")
            if "Description" in heading:
                print(f"  ✓ Found Description block")
                content_el = block.locator("div.collapsible-content_inner.product_description")
                if content_el.count() > 0:
                    full_text = content_el.inner_text().strip()
                    print(f"    Description length: {len(full_text)} characters")
                    
                    # Extract Features section as specifications
                    print(f"    → Looking for Features section...")
                    try:
                        features_ul = content_el.locator("xpath=.//h2[contains(text(), 'Features')]/following-sibling::ul[1]")
                        if features_ul.count() > 0:
                            specs_text = features_ul.inner_text().strip()
                            specifications = self.normalize_text(specs_text)
                            print(f"  ✓ Found Features section")
                            print(f"    Specifications length: {len(specifications)} characters")
                    except:
                        print(f"    ⚠ Features section not found")
                    
                    # If Features not found, try to extract specification data from text
                    if not specifications:
                        print(f"    → Extracting specifications from text...")
                        spec_lines = []
                        lines = full_text.split('\n')
                        for line in lines:
                            line = line.strip()
                            if any(keyword in line for keyword in ['Item Weight:', 'Product Dimensions:', 'Adult Assembly Required:', 'Warning:']):
                                spec_lines.append(line)
                        if spec_lines:
                            specifications = ' '.join(spec_lines)
                            print(f"  ✓ Extracted specifications from text")
                            print(f"    Specifications length: {len(specifications)} characters")
                    
                    description = self.normalize_text(full_text)
                break
        
        if not description:
            print(f"  ⚠ Description not found")
        
        # Extract SKU from product meta
        print(f"  → Extracting product SKU...")
        sku_el = page.locator("span.product__sku")
        sku = sku_el.inner_text().strip() if sku_el.count() > 0 else ""
        if sku:
            print(f"  ✓ SKU: {sku}")
        else:
            print(f"  ⚠ SKU not found")
        
        # Extract images from media-gallery
        print(f"  → Extracting product images...")
        image_elements = page.locator("media-gallery .media-gallery__image img").all()
        print(f"    Found {len(image_elements)} image element(s)")
        images = []
        seen_urls = set()
        
        for img in image_elements:
            src = img.get_attribute("src")
            if src:
                clean_url = self.clean_image_url(src)
                if clean_url not in seen_urls:
                    seen_urls.add(clean_url)
                    images.append(clean_url)
                    print(f"      Added image: {clean_url[:60]}...")
        
        print(f"  ✓ Found {len(images)} image(s)")
        
        return Product(
            title=title,
            price=price,
            description=description,
            specifications=specifications,
            images=images,
            sku=sku,
            url=product_url
        )
