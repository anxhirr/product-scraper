from scraper.base_scraper import BaseScraper
from scraper.hape_scraper import HapeScraper
from scraper.elrincondelosgenios_scraper import ElRinconDeLosGeniosScraper
from scraper.elrincondelosgenios_api_scraper import ElRinconDeLosGeniosApiScraper


# Registry mapping site identifiers to scraper classes
SCRAPER_REGISTRY = {
    "hape": HapeScraper,
    "elrincondelosgenios": ElRinconDeLosGeniosScraper,
    "elrincondelosgenios_api": ElRinconDeLosGeniosApiScraper,
}


def get_scraper(site: str) -> BaseScraper:
    """
    Factory function that returns an instance of the appropriate scraper for the given site.
    
    Args:
        site: Site identifier (e.g., "hape", "elrincondelosgenios")
    
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
