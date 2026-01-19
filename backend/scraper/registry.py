from scraper.base_scraper import BaseScraper
# from scraper.hape_scraper import HapeScraper
from scraper.hape_global_scraper import HapeGlobalScraper
from scraper.elrincondelosgenios_scraper import ElRinconDeLosGeniosScraper
from scraper.elrincondelosgenios_api_scraper import ElRinconDeLosGeniosApiScraper


# Registry mapping site identifiers to scraper classes
SCRAPER_REGISTRY = {
    # "hape": HapeScraper,
    "hape": HapeGlobalScraper,
    "hape_global": HapeGlobalScraper,
    "elrincondelosgenios": ElRinconDeLosGeniosScraper,
    "elrincondelosgenios_api": ElRinconDeLosGeniosApiScraper,
}

# Brand to sites mapping (ordered list: primary, fallback, etc.)
BRAND_TO_SITES_MAP = {
    "hape": ["hape", "hape_global"],
    "elrincondelosgenios": ["elrincondelosgenios_api", "elrincondelosgenios"],
}


def get_scraper(site: str) -> BaseScraper:
    """
    Factory function that returns an instance of the appropriate scraper for the given site.
    
    Args:
        site: Site identifier (e.g., "hape", "hape_global", "elrincondelosgenios")
    
    Returns:
        An instance of the appropriate scraper class
    
    Raises:
        ValueError: If the site identifier is not found in the registry
    """
    site_lower = site.lower()
    if site_lower not in SCRAPER_REGISTRY:
        available_sites = ", ".join(SCRAPER_REGISTRY.keys())
        raise ValueError(
            f"Unknown site: '{site}'. Available sites: {available_sites}"
        )
    
    scraper_class = SCRAPER_REGISTRY[site_lower]
    return scraper_class()


def get_available_sites() -> list[str]:
    """Returns a list of available site identifiers."""
    return list(SCRAPER_REGISTRY.keys())


def get_sites_for_brand(brand: str) -> list[str]:
    """
    Returns an ordered list of site identifiers for a given brand.
    The list is ordered by priority (primary, fallback, etc.).
    
    Args:
        brand: Brand identifier (e.g., "hape", "elrincondelosgenios")
    
    Returns:
        Ordered list of site identifiers for the brand
    
    Raises:
        ValueError: If the brand identifier is not found in the mapping
    """
    brand_lower = brand.lower()
    if brand_lower not in BRAND_TO_SITES_MAP:
        available_brands = ", ".join(BRAND_TO_SITES_MAP.keys())
        raise ValueError(
            f"Unknown brand: '{brand}'. Available brands: {available_brands}"
        )
    
    return BRAND_TO_SITES_MAP[brand_lower]


def get_available_brands() -> list[str]:
    """Returns a list of available brand identifiers."""
    return list(BRAND_TO_SITES_MAP.keys())
