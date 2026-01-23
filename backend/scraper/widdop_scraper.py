from playwright.sync_api import Page
import time
from scraper.base_scraper import BaseScraper
from scraper.models import Product


class WiddopScraper(BaseScraper):
    """Scraper implementation for widdop.co.uk (Bambino brand)"""
    
    def get_base_url(self) -> str:
        return "https://www.widdop.co.uk"
    
    def perform_search(self, page: Page, search_text: str, navigation_delay: float = 0) -> None:
        """Performs search on Widdop website by navigating directly to search URL with barcode."""
        print(f"  → Navigating to search URL with barcode: '{search_text}'...")
        
        # Navigate directly to search URL with barcode as term parameter
        search_url = f"{self.get_base_url()}/search?term={search_text}"
        page.goto(search_url, wait_until="load")
        
        if navigation_delay > 0:
            time.sleep(navigation_delay)
        
        # Wait for search results container to be visible
        print(f"  → Waiting for search results to load...")
        product_list_grid = page.locator(".product-list__grid")
        product_list_grid.wait_for(state="visible", timeout=15000)
        print(f"  ✓ Search results container is visible")
        
        # Wait for at least one product to appear
        product_items = page.locator(".product-list__grid__product")
        try:
            product_items.first.wait_for(state="visible", timeout=15000)
            print(f"  ✓ Product items are visible")
        except Exception as e:
            print(f"  ⚠ No products found in search results: {str(e)}")
            raise Exception(f"No products found for barcode: {search_text}")
    
    def get_first_product_link(self, page: Page, search_text: str) -> str:
        """Extracts the first product link from Widdop search results."""
        print(f"  → Looking for product links in search results...")
        
        # Wait for product list to be visible
        product_list_grid = page.locator(".product-list__grid")
        product_list_grid.wait_for(state="visible", timeout=15000)
        
        # Find the first product in the grid
        first_product = page.locator(".product-list__grid__product").first
        first_product.wait_for(state="visible", timeout=15000)
        print(f"  ✓ Found first product")
        
        # Try to find product link - check both image link and name link
        product_link = None
        
        # Try image link first
        image_link = first_product.locator(".product-summary__image a").first
        if image_link.count() > 0:
            product_link = image_link
            print(f"  → Found product link via image")
        else:
            # Try name link
            name_link = first_product.locator(".product-summary__name a").first
            if name_link.count() > 0:
                product_link = name_link
                print(f"  → Found product link via name")
        
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
        """Extracts product data from Widdop product page."""
        print(f"  → Extracting product data...")
        
        # Wait for product page to load - wait for product container instead of title
        print(f"  → Waiting for product page to load...")
        product_container = page.locator("#product-page, [data-product-id]").first
        product_container.wait_for(state="attached", timeout=15000)
        print(f"  ✓ Product page loaded")
        
        # Extract title - one of the title elements will exist (desktop or mobile)
        print(f"  → Extracting product title...")
        title = ""
        
        # Try desktop title first
        desktop_title = page.locator("h1.product-information__name").first
        if desktop_title.count() > 0:
            title = desktop_title.inner_text().strip()
            print(f"  ✓ Title from desktop element: {title[:50]}..." if len(title) > 50 else f"  ✓ Title: {title}")
        
        # If desktop title is empty, try mobile title
        if not title:
            mobile_title = page.locator(".product-information__name__mobile").first
            if mobile_title.count() > 0:
                title = mobile_title.inner_text().strip()
                print(f"  ✓ Title from mobile element: {title[:50]}..." if len(title) > 50 else f"  ✓ Title: {title}")
        
        if not title:
            raise Exception("Product title not found")
        
        # Extract SKU
        print(f"  → Extracting product SKU...")
        sku = ""
        # Try product code element first
        sku_element = page.locator(".product-information__product-code strong")
        if sku_element.count() > 0:
            sku = sku_element.inner_text().strip()
            print(f"  ✓ SKU from product code: {sku}")
        else:
            # Try data-gtm-id attribute on product container
            product_container = page.locator("#product-page, [data-product-id]").first
            if product_container.count() > 0:
                gtm_id = product_container.get_attribute("data-gtm-id")
                if gtm_id:
                    sku = gtm_id.strip()
                    print(f"  ✓ SKU from data-gtm-id: {sku}")
        
        if not sku:
            print(f"  ⚠ SKU not found")
        
        # Price is not available (requires login)
        price = ""
        print(f"  → Price: Not available (login required)")
        
        # Extract description
        print(f"  → Extracting product description...")
        description = ""
        
        # Try to expand Description accordion if needed
        description_tab = page.locator("#collapse-descriptionTab")
        if description_tab.count() > 0:
            # Check if accordion is collapsed
            is_collapsed = description_tab.get_attribute("class")
            if is_collapsed and "collapse" in is_collapsed and "in" not in is_collapsed:
                # Click to expand
                description_button = page.locator('a[href="#collapse-descriptionTab"]').first
                if description_button.count() > 0:
                    description_button.click()
                    page.wait_for_timeout(500)
                    print(f"  → Expanded Description accordion")
        
        # Extract description text
        description_element = page.locator("#descriptionTab .description, .panel-body#descriptionTab .description").first
        if description_element.count() > 0:
            description = description_element.inner_text().strip()
            description = self.normalize_text(description)
            print(f"  ✓ Description length: {len(description)} characters")
        else:
            print(f"  ⚠ Description not found")
        
        # Extract specifications
        print(f"  → Extracting product specifications...")
        specifications = ""
        
        # Try to expand Specification accordion if needed
        spec_tab = page.locator("#collapse-specificationTab")
        if spec_tab.count() > 0:
            # Check if accordion is collapsed
            is_collapsed = spec_tab.get_attribute("class")
            if is_collapsed and "collapse" in is_collapsed and "in" not in is_collapsed:
                # Click to expand
                spec_button = page.locator('a[href="#collapse-specificationTab"]').first
                if spec_button.count() > 0:
                    spec_button.click()
                    page.wait_for_timeout(500)
                    print(f"  → Expanded Specification accordion")
        
        # Extract specification items
        spec_items = page.locator("#specificationTab .specification, .panel-body#specificationTab .specification").all()
        print(f"    Found {len(spec_items)} specification item(s)")
        
        if spec_items:
            spec_lines = []
            for item in spec_items:
                # Extract key from .filter-name span
                key_element = item.locator(".filter-name").first
                # Extract value from .filter-class span
                value_element = item.locator(".filter-class").first
                
                if key_element.count() > 0 and value_element.count() > 0:
                    key = key_element.inner_text().strip()
                    value = value_element.inner_text().strip()
                    
                    # Skip empty keys/values
                    if key and value:
                        spec_lines.append(f"{key}: {value}")
                        print(f"      Added spec: {key}: {value[:30]}..." if len(value) > 30 else f"      Added spec: {key}: {value}")
            
            if spec_lines:
                specifications = "\n".join(spec_lines)
                print(f"  ✓ Formatted {len(spec_lines)} specification(s)")
            else:
                print(f"  ⚠ No valid specifications found")
        else:
            print(f"  ⚠ No specification items found")
        
        # Extract images
        print(f"  → Extracting product images...")
        images = []
        seen_urls = set()
        
        # Extract from thumbnail links (magiczoom_thumbs)
        thumb_links = page.locator(".magiczoom_thumbs a").all()
        print(f"    Found {len(thumb_links)} thumbnail link(s)")
        
        for thumb_link in thumb_links:
            # Try data-image attribute first, then href
            image_url = thumb_link.get_attribute("data-image")
            if not image_url:
                image_url = thumb_link.get_attribute("href")
            
            if image_url:
                clean_url = self.clean_image_url(image_url)
                if clean_url and clean_url not in seen_urls:
                    seen_urls.add(clean_url)
                    images.append(clean_url)
                    print(f"      Added image from thumb: {clean_url[:60]}...")
        
        # Also try to get main image
        main_image = page.locator(".product-images-container__primary-image img[data-main-image], .product-images-container__primary-image img").first
        if main_image.count() > 0:
            main_src = main_image.get_attribute("src")
            if not main_src:
                main_src = main_image.get_attribute("data-src")
            
            if main_src:
                clean_url = self.clean_image_url(main_src)
                if clean_url and clean_url not in seen_urls:
                    seen_urls.add(clean_url)
                    images.insert(0, clean_url)  # Insert at beginning as primary
                    print(f"      Added main image: {clean_url[:60]}...")
        
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
