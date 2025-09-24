from ..const import HANDBALL_NET_LOGO_PREFIX, HANDBALL_NET_WEB_URL

class URLHandler:
    """Handler für URL-Operationen"""

    @staticmethod
    def normalize_logo_url(logo_url: str) -> str:
        """Convert handball-net: logo URL to full HTTPS URL"""
        if logo_url and logo_url.startswith(HANDBALL_NET_LOGO_PREFIX):
            return logo_url.replace(HANDBALL_NET_LOGO_PREFIX, HANDBALL_NET_WEB_URL)
        return logo_url