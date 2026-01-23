from typing import Optional, List
from playwright.sync_api import Page


class CookieConsentService:
    """Service for handling cookie consent overlays on web pages."""
    
    # Default selectors for common cookie consent overlays
    DEFAULT_SELECTORS = [
        "#coiOverlay",
        ".coiOverlay-container",
        "#cookie-information-template-wrapper"
    ]
    
    @staticmethod
    def handle(page: Page, custom_selectors: Optional[List[str]] = None) -> None:
        """
        Handles cookie consent overlays by detecting and hiding them programmatically.
        
        This method checks for common cookie consent overlay selectors and hides them
        using JavaScript, which is the most reliable method for dismissing these overlays.
        
        Args:
            page: The Playwright page object
            custom_selectors: Optional list of custom CSS selectors for site-specific overlays.
                            If not provided, uses default common selectors.
        """
        # Use custom selectors if provided, otherwise use defaults
        selectors = custom_selectors if custom_selectors else CookieConsentService.DEFAULT_SELECTORS
        
        # Combine selectors into a single locator string
        selector_string = ", ".join(selectors)
        
        print(f"  → Checking for cookie consent overlay...")
        cookie_overlay = page.locator(selector_string)
        
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
                    # Build JavaScript selector string for querySelectorAll
                    # Format: "#coiOverlay, .coiOverlay-container, #cookie-information-template-wrapper"
                    js_selector_string = ", ".join(selectors)
                    page.evaluate(f"""
                        document.querySelectorAll('{js_selector_string}').forEach(el => {{
                            el.setAttribute('aria-hidden', 'true');
                            el.style.display = 'none';
                            el.style.pointerEvents = 'none';
                            el.style.zIndex = '-1';
                        }});
                    """)
                    page.wait_for_timeout(500)
                    print(f"  ✓ Hid cookie overlay programmatically")
                except Exception as e:
                    print(f"  ⚠ Failed to hide cookie overlay via JavaScript: {str(e)}")
