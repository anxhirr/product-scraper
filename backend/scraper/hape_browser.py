from playwright.sync_api import sync_playwright

def scrape_hape_product(search_text: str):
    print(f"[Step 1/8] Launching browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print(f"[Step 2/8] Navigating to Hape website...")
        page.goto("https://toys.hape.com/", wait_until="load")

        print(f"[Step 3/8] Searching for '{search_text}'...")
        # Search
        search_input = page.locator("input[type='search']")
        search_input.fill(search_text)
        search_input.press("Enter")

        print(f"[Step 4/8] Waiting for search results...")
        # Wait for first product link
        first_product = page.locator('a[href*="/products/"]').first
        first_product.wait_for(state="visible", timeout=15000)
        href = first_product.get_attribute("href")
        
        print(f"[Step 5/8] Navigating to product page...")
        page.goto(f"https://toys.hape.com{href}")

        print(f"[Step 6/8] Waiting for product details to load...")
        # Wait for product title
        title_element = page.locator("h1.product-detail__title")
        title_element.wait_for(state="visible", timeout=15000)

        print(f"[Step 7/8] Extracting product data...")
        # Extract data
        title = page.locator("h1.product-detail__title").inner_text().strip()
        price = page.locator("span.price.price-same-style.heading-style").inner_text().strip()
        description_el = page.locator("div.product-detail__description")
        description = description_el.inner_text().strip() if description_el.count() > 0 else ""
        
        # Extract SKU from product meta
        sku_el = page.locator("span.product__sku")
        sku = sku_el.inner_text().strip() if sku_el.count() > 0 else ""
        
        # Extract images from media-gallery (main product images)
        image_elements = page.locator("media-gallery .media-gallery__image img").all()
        images = []
        seen_urls = set()  # To avoid duplicates
        
        for img in image_elements:
            src = img.get_attribute("src")
            if src:
                # Convert protocol-relative URLs (//) to https://
                if src.startswith("//"):
                    src = "https:" + src
                # Remove query parameters to get clean image URL
                clean_url = src.split("?")[0] if "?" in src else src
                # Only add if we haven't seen this URL before
                if clean_url not in seen_urls:
                    seen_urls.add(clean_url)
                    images.append(clean_url)

        print(f"[Step 8/8] Closing browser...")
        browser.close()
        
        print(f"✓ Scraping completed successfully!")

        return {
            "title": title,
            "price": price,
            "description": description,
            "images": images,
            "sku": sku,
            "vendor": "",    # same
            "variants": []   # same
        }
