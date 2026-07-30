"""
CSS Library Provider - Fetches CSS icon libraries.

Supports:
- Bootstrap Icons (CDN)
- Font Awesome (CDN)

Returns CDN URLs for inclusion in generated projects.
"""

import logging
from enum import Enum
from pydantic import BaseModel
from typing import Optional, List


logger = logging.getLogger(__name__)


class CSSLibrary(str, Enum):
    """Supported CSS/icon font libraries."""
    BOOTSTRAP_ICONS = "bootstrap_icons"
    FONT_AWESOME = "font_awesome"
   


class CSSAsset(BaseModel):
    """CSS library asset."""
    
    asset_id: str
    library: CSSLibrary
    name: str
    cdn_url: str
    format: str  # css, font, woff2, etc.
    version: str
    license: str


class CSSLibraryProvider:
    """Provide CSS libraries and icon fonts via CDN."""
    
    def __init__(self):
        self.libraries = {
            CSSLibrary.BOOTSTRAP_ICONS: {
                "name": "Bootstrap Icons",
                "cdn_url": "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css",
                "format": "css",
                "version": "1.11.0",
                "license": "MIT",
                "icon_prefix": "bi",
            },
            CSSLibrary.FONT_AWESOME: {
                "name": "Font Awesome",
                "cdn_url": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",
                "format": "css",
                "version": "6.4.0",
                "license": "Free",
                "icon_prefix": "fa",
            },
        }
    
    def select_library(self, icon_purpose: str) -> CSSLibrary:
        purpose = icon_purpose.lower()

        if any(word in purpose for word in ["brand", "logo", "social", "payment"]):
            return CSSLibrary.FONT_AWESOME

        return CSSLibrary.BOOTSTRAP_ICONS 
    
    def get_library_css(
        self,
        library: Optional[CSSLibrary] = None,
    ) -> Optional[CSSAsset]:
        """
        Get CSS/font library asset.
        
        Args:
            library: Which library to use
            
        Returns:
            CSSAsset with CDN information
        """
        if library is None:
            library = CSSLibrary.BOOTSTRAP_ICONS
        
        if library not in self.libraries:
            logger.warning(f"Unknown CSS library: {library}")
            return None
        
        config = self.libraries[library]
        
        return CSSAsset(
            asset_id=library.value,
            library=library,
            name=config["name"],
            cdn_url=config["cdn_url"],
            format=config["format"],
            version=config["version"],
            license=config["license"],
        )
    
    def get_all_libraries(self) -> List[CSSAsset]:
        """Get all available libraries."""
        assets = []
        for library in CSSLibrary:
            asset = self.get_library_css(library)
            if asset:
                assets.append(asset)
        return assets
