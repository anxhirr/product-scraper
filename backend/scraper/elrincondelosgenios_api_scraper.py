import requests
from typing import Any, Dict, List
from playwright.sync_api import Page
from scraper.base_scraper import BaseScraper
from scraper.models import Product


class ElRinconDeLosGeniosApiScraper(BaseScraper):
    """API-based scraper implementation for elrincondelosgenios.com using their search API."""
    
    API_URL = "https://elrincondelosgenios.com/module/iqitsearch/searchiqit"
    
    def get_base_url(self) -> str:
        """Returns the base URL (not used for API-based scraping)."""
        return "https://elrincondelosgenios.com/"
    
    def perform_search(self, page: Page, search_text: str) -> None:
        """Not used for API-based scraping."""
        pass
    
    def get_first_product_link(self, page: Page, search_text: str) -> str:
        """Not used for API-based scraping."""
        return ""
    
    def extract_product_data(self, page: Page, product_url: str) -> Product:
        """Not used for API-based scraping."""
        return Product(
            title="",
            sku="",
            price="",
            description="",
            specifications="",
            images=[],
            url=""
        )
    
    def scrape_product(self, search_text: str) -> Product:
        """
        Main scraping method that calls the API and extracts product data.
        Overrides the base class method to use API calls instead of browser automation.
        """
        print(f"[Step 1/3] Calling search API for '{search_text}'...")
        
        # Prepare form data
        form_data = {
            "s": search_text,
            "resultsPerPage": "10",
            "ajax": "true"
        }
        
        # Make POST request
        try:
            response = requests.post(
                self.API_URL,
                data=form_data,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json, text/html, */*"
                },
                timeout=30
            )
            response.raise_for_status()
            print(f"  ✓ API request successful (status: {response.status_code})")
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
        
        print(f"[Step 2/3] Parsing API response...")
        
        # Try to parse as JSON first
        try:
            data = response.json()
            product = self._parse_json_response(data, search_text)
        except ValueError:
            # If not JSON, try parsing as HTML
            print(f"  → Response is not JSON, trying HTML parsing...")
            product = self._parse_html_response(response.text, search_text)
        
        print(f"[Step 3/3] ✓ Product data extracted successfully!")
        return product
    
    def _parse_json_response(self, data: Any, search_text: str) -> Product:
        """Parse JSON response from the API."""
        # Try to find products in the response
        products = []
        
        # Common JSON response structures
        if isinstance(data, dict):
            # Try different possible keys
            if "products" in data:
                products = data["products"]
            elif "results" in data:
                products = data["results"]
            elif "items" in data:
                products = data["items"]
            elif "data" in data and isinstance(data["data"], list):
                products = data["data"]
            elif "data" in data and isinstance(data["data"], dict) and "products" in data["data"]:
                products = data["data"]["products"]
        elif isinstance(data, list):
            products = data
        
        if not products or len(products) == 0:
            raise Exception("No products found in API response")
        
        # Get the first product
        first_product = products[0] if isinstance(products, list) else products
        
        if not isinstance(first_product, dict):
            raise Exception("Invalid product data structure in API response")
        
        # Extract product data based on actual API structure
        title = first_product.get("name", "")
        sku = first_product.get("reference", "")
        price = first_product.get("price", "")
        description_html = first_product.get("description_short", "")
        url = first_product.get("url", "") or first_product.get("link", "")
        
        # Strip HTML from description
        description = self._strip_html(description_html) if description_html else ""
        
        # Build specifications from available fields
        specs_parts = []
        if first_product.get("manufacturer_name"):
            specs_parts.append(f"Brand: {first_product['manufacturer_name']}")
        if first_product.get("category_name"):
            specs_parts.append(f"Category: {first_product['category_name']}")
        if first_product.get("tax_name"):
            specs_parts.append(f"Tax: {first_product['tax_name']}")
        specifications = " | ".join(specs_parts)
        
        # Extract images from cover.bySize structure
        images = []
        cover = first_product.get("cover", {})
        if isinstance(cover, dict):
            by_size = cover.get("bySize", {})
            if isinstance(by_size, dict):
                # Prefer larger images, fallback to smaller ones
                for size_key in ["thickbox_default", "large_default", "home_default", "medium_default", "small_default"]:
                    if size_key in by_size:
                        size_data = by_size[size_key]
                        if isinstance(size_data, dict) and "url" in size_data:
                            image_url = size_data["url"]
                            if image_url:
                                images.append(self.clean_image_url(image_url))
                                break  # Use the first (largest) available image
        
        # If no images from bySize, try direct cover fields
        if not images:
            if isinstance(cover, dict):
                for key in ["large", "medium", "small"]:
                    if key in cover and isinstance(cover[key], dict) and "url" in cover[key]:
                        image_url = cover[key]["url"]
                        if image_url:
                            images.append(self.clean_image_url(image_url))
                            break
        
        # Ensure URL is absolute
        if url and not url.startswith("http"):
            url = f"https://elrincondelosgenios.com{url}" if url.startswith("/") else f"https://elrincondelosgenios.com/{url}"
        
        return Product(
            title=title or f"Product: {search_text}",
            sku=sku or "N/A",
            price=price or "Price not available",
            description=self.normalize_text(description) if description else "",
            specifications=specifications,
            images=images,
            url=url or f"https://elrincondelosgenios.com/"
        )
    
    def _parse_html_response(self, html: str, search_text: str) -> Product:
        """Parse HTML response from the API (fallback if JSON parsing fails)."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, "lxml")
        
        # Try to find product elements
        product_elements = soup.find_all(["div", "article", "li"], class_=lambda x: x and ("product" in x.lower() or "item" in x.lower()))
        
        if not product_elements:
            raise Exception("No product elements found in HTML response")
        
        first_product = product_elements[0]
        
        # Extract title
        title_elem = first_product.find(["h1", "h2", "h3", "h4", "a"], class_=lambda x: x and ("title" in x.lower() or "name" in x.lower()))
        title = title_elem.get_text(strip=True) if title_elem else ""
        if not title:
            title = first_product.find("a", href=True)
            title = title.get_text(strip=True) if title else ""
        
        # Extract URL
        url_elem = first_product.find("a", href=True)
        url = url_elem["href"] if url_elem else ""
        if url and not url.startswith("http"):
            url = f"https://elrincondelosgenios.com{url}" if url.startswith("/") else f"https://elrincondelosgenios.com/{url}"
        
        # Extract price
        price_elem = first_product.find(class_=lambda x: x and "price" in x.lower())
        price = price_elem.get_text(strip=True) if price_elem else ""
        
        # Extract SKU
        sku_elem = first_product.find(class_=lambda x: x and "sku" in x.lower())
        sku = sku_elem.get_text(strip=True) if sku_elem else ""
        
        # Extract description
        desc_elem = first_product.find(class_=lambda x: x and "description" in x.lower() or "desc" in x.lower())
        description = desc_elem.get_text(strip=True) if desc_elem else ""
        
        # Extract images
        images = []
        img_elem = first_product.find("img")
        if img_elem and img_elem.get("src"):
            images.append(self.clean_image_url(img_elem["src"]))
        if img_elem and img_elem.get("data-src"):
            images.append(self.clean_image_url(img_elem["data-src"]))
        
        return Product(
            title=title or f"Product: {search_text}",
            sku=sku or "N/A",
            price=price or "Price not available",
            description=self.normalize_text(description),
            specifications="",
            images=images,
            url=url or f"https://elrincondelosgenios.com/"
        )
    
    def _extract_field(self, data: Dict[str, Any], possible_keys: List[str]) -> str:
        """Extract a field from data using multiple possible key names."""
        if not isinstance(data, dict):
            return ""
        
        for key in possible_keys:
            if key in data:
                value = data[key]
                if value is not None:
                    return str(value)
        return ""
    
    def _strip_html(self, html: str) -> str:
        """Strip HTML tags from a string."""
        if not html:
            return ""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        return soup.get_text(separator=" ", strip=True)
