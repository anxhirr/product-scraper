from scraper.base_scraper import BaseScraper
# from scraper.hape_scraper import HapeScraper
from scraper.hape_global_scraper import HapeGlobalScraper
from scraper.rockahula_scraper import RockahulaScraper
from scraper.donebydeer_scraper import DoneByDeerScraper
from scraper.widdop_scraper import WiddopScraper
from scraper.liewood_scraper import LiewoodScraper


# Registry mapping site identifiers to scraper classes
SCRAPER_REGISTRY = {
    # "hape": HapeScraper,
    "hape": HapeGlobalScraper,
    "hape_global": HapeGlobalScraper,
    "rockahula": RockahulaScraper,
    "donebydeer": DoneByDeerScraper,
    "widdop": WiddopScraper,
    "liewood": LiewoodScraper,
}

# Brand to sites mapping (ordered list: primary, etc.)
BRAND_TO_SITES_MAP = {
    "hape": ["hape", "hape_global"],
    "rockahula": ["rockahula"],
    "done_by_deer": ["donebydeer"],
    "bambino": ["widdop"],
    "liewood": ["liewood"],
}


def get_scraper(site: str) -> BaseScraper:
    """
    Factory function that returns an instance of the appropriate scraper for the given site.
    
    Args:
        site: Site identifier (e.g., "hape", "hape_global", "rockahula")
    
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
    The list is ordered by priority.
    
    Args:
        brand: Brand identifier (e.g., "hape", "rockahula", "done_by_deer")
    
    Returns:
        Ordered list of site identifiers for the brand
    
    Raises:
        ValueError: If the brand identifier is not found in the mapping
    """
    brand_lower = brand.lower().strip()
    
    # Try exact match
    if brand_lower in BRAND_TO_SITES_MAP:
        return BRAND_TO_SITES_MAP[brand_lower]
    
    # If not found, show available brands
    available_brands = ", ".join(BRAND_TO_SITES_MAP.keys())
    raise ValueError(
        f"Unknown brand: '{brand}'. Available brands: {available_brands}"
    )


def get_available_brands() -> list[str]:
    """Returns a list of available brand identifiers."""
    return list(BRAND_TO_SITES_MAP.keys())
