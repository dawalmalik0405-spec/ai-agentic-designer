"""
Icon Library Provider - Fetches SVG icons from free icon libraries.

Supports:
- Feather Icons (https://feathericons.com)
- Lucide Icons (https://lucide.dev)
- Material Icons (https://fonts.google.com/icons)
- Phosphor Icons (https://phosphoricons.com)

Returns SVG icon data or CDN URLs.
"""

import logging
from typing import Optional, Dict, List
from enum import Enum
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class IconLibrary(str, Enum):
    """Supported icon libraries."""
    FEATHER = "feather"
    LUCIDE = "lucide"
    MATERIAL = "material"
    PHOSPHOR = "phosphor"


class IconData(BaseModel):
    """Icon data from library."""
    
    icon_id: str
    library: IconLibrary
    name: str
    svg_url: str  # Direct SVG URL or CDN
    cdn_url: str  # CDN fallback
    format: str = "svg"
    viewbox: str = "0 0 24 24"
    stroke_width: int = 2


class IconLibraryProvider:
    """Fetch icons from various free libraries."""
    
    def __init__(self):
        # Icon library metadata
        self.libraries: Dict[IconLibrary, Dict] = {
            IconLibrary.FEATHER: {
                "name": "Feather Icons",
                "base_url": "https://raw.githubusercontent.com/feathericons/feather/master/icons",
                "format": "svg",
                "viewbox": "0 0 24 24",
                "stroke_width": 2,
            },
            IconLibrary.LUCIDE: {
                "name": "Lucide Icons",
                "base_url": "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons",
                "format": "svg",
                "viewbox": "0 0 24 24",
                "stroke_width": 2,
            },
            IconLibrary.MATERIAL: {
                "name": "Material Icons",
                "base_url": "https://fonts.gstatic.com/s/i/materialsymbols",
                "format": "svg",
                "viewbox": "0 0 24 24",
                "stroke_width": 1,
            },
            IconLibrary.PHOSPHOR: {
                "name": "Phosphor Icons",
                "base_url": "https://raw.githubusercontent.com/phosphor-icons/core/main/assets/regular",
                "format": "svg",
                "viewbox": "0 0 256 256",
                "stroke_width": 2,
            },
        }
    
    def select_library(self, icon_purpose: str) -> IconLibrary:
        """
        Select appropriate icon library based on icon purpose.
        
        Args:
            icon_purpose: What the icon is for (e.g., "social", "navigation", "UI")
            
        Returns:
            Recommended IconLibrary
        """
        purpose_lower = icon_purpose.lower()
        
        if "social" in purpose_lower or "brand" in purpose_lower:
            return IconLibrary.FEATHER  # Good for social media
        elif "ui" in purpose_lower or "interface" in purpose_lower:
            return IconLibrary.LUCIDE  # Modern UI icons
        elif "material" in purpose_lower or "design" in purpose_lower:
            return IconLibrary.MATERIAL  # Material Design
        else:
            return IconLibrary.FEATHER  # Default: Feather
    
    def get_icon_url(
        self,
        icon_name: str,
        library: Optional[IconLibrary] = None,
    ) -> Optional[IconData]:
        """
        Get SVG URL for an icon.
        
        Args:
            icon_name: Icon name (e.g., "heart", "star", "user")
            library: Which library to use, or None to auto-select
            
        Returns:
            IconData with SVG URL or None if not found
        """
        if library is None:
            library = IconLibrary.FEATHER
        
        if library not in self.libraries:
            logger.warning(f"Unknown icon library: {library}")
            return None
        
        lib_config = self.libraries[library]
        
        try:
            if library == IconLibrary.FEATHER:
                return self._get_feather_icon(icon_name, lib_config)
            elif library == IconLibrary.LUCIDE:
                return self._get_lucide_icon(icon_name, lib_config)
            elif library == IconLibrary.MATERIAL:
                return self._get_material_icon(icon_name, lib_config)
            elif library == IconLibrary.PHOSPHOR:
                return self._get_phosphor_icon(icon_name, lib_config)
        except Exception as e:
            logger.warning(f"Failed to get icon: {e}")
            return None
    
    def _get_feather_icon(self, name: str, config: Dict) -> Optional[IconData]:
        """Get Feather icon."""
        svg_url = f"{config['base_url']}/{name}.svg"
        
        return IconData(
            icon_id=f"feather_{name}",
            library=IconLibrary.FEATHER,
            name=name,
            svg_url=svg_url,
            cdn_url=svg_url,  # Feather uses raw GitHub
            format=config["format"],
            viewbox=config["viewbox"],
            stroke_width=config["stroke_width"],
        )
    
    def _get_lucide_icon(self, name: str, config: Dict) -> Optional[IconData]:
        """Get Lucide icon."""
        # Lucide uses filename convention: name.svg in regular folder
        svg_url = f"{config['base_url']}/regular/{name}.svg"
        
        return IconData(
            icon_id=f"lucide_{name}",
            library=IconLibrary.LUCIDE,
            name=name,
            svg_url=svg_url,
            cdn_url=svg_url,
            format=config["format"],
            viewbox=config["viewbox"],
            stroke_width=config["stroke_width"],
        )
    
    def _get_material_icon(self, name: str, config: Dict) -> Optional[IconData]:
        """Get Material icon (CDN-based)."""
        # Material Icons uses CDN URL structure
        cdn_url = f"https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0"
        
        return IconData(
            icon_id=f"material_{name}",
            library=IconLibrary.MATERIAL,
            name=name,
            svg_url=cdn_url,
            cdn_url=cdn_url,
            format="font",  # Material uses font icons
            viewbox=config["viewbox"],
            stroke_width=config["stroke_width"],
        )
    
    def _get_phosphor_icon(self, name: str, config: Dict) -> Optional[IconData]:
        """Get Phosphor icon."""
        svg_url = f"{config['base_url']}/{name}.svg"
        
        return IconData(
            icon_id=f"phosphor_{name}",
            library=IconLibrary.PHOSPHOR,
            name=name,
            svg_url=svg_url,
            cdn_url=svg_url,
            format=config["format"],
            viewbox=config["viewbox"],
            stroke_width=config["stroke_width"],
        )
