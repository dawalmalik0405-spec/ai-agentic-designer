"""
Asset Resolver - Intelligently routes assets through different source paths.

Routes assets through:
- STOCK: Search API for existing high-quality assets
- GENERATE: Image generation model for custom visuals
- ICON_CSS: Icon libraries and CSS frameworks
- CLIENT: Client-provided assets
"""

import logging
from typing import List

from schema.asset import AssetRequirement, AssetType, SourceStrategy, AssetPriority
from schema.asset_resolver import (
    ResolvedAsset,
    ResolutionPath,
    ResolverOutput,
)


logger = logging.getLogger(__name__)


class AssetResolver:
    """Intelligent asset resolver that routes assets through appropriate paths."""
    
    def __init__(self):
        # Define routing rules
        self.icon_types = {AssetType.ICON, AssetType.LOGO}
        self.generatable_types = {
            AssetType.IMAGE,
            AssetType.ILLUSTRATION,
            AssetType.BACKGROUND,
            AssetType.SVG_DIAGRAM,
        }
    
    def resolve(self, asset_output) -> ResolverOutput:
        """
        Resolve assets to appropriate generation/sourcing paths.
        
        Args:
            asset_output: AssetOutput with list of AssetRequirements
            
        Returns:
            ResolverOutput with resolved assets and routing decisions
        """
        resolved_assets: List[ResolvedAsset] = []
        
        for requirement in asset_output.assets:
            resolved = self._resolve_single_asset(requirement)
            resolved_assets.append(resolved)
        
        # Count by path
        stock_count = sum(1 for r in resolved_assets if r.resolution_path == ResolutionPath.STOCK)
        generate_count = sum(1 for r in resolved_assets if r.resolution_path == ResolutionPath.GENERATE)
        icon_css_count = sum(1 for r in resolved_assets if r.resolution_path == ResolutionPath.ICON_CSS)
        client_count = sum(1 for r in resolved_assets if r.resolution_path == ResolutionPath.CLIENT)
        
        logger.info(
            "Asset resolution complete",
            extra={
                "total": len(resolved_assets),
                "stock": stock_count,
                "generate": generate_count,
                "icon_css": icon_css_count,
                "client": client_count,
            }
        )
        
        return ResolverOutput(
            total_assets=len(resolved_assets),
            resolved_assets=resolved_assets,
            stock_count=stock_count,
            generate_count=generate_count,
            icon_css_count=icon_css_count,
            client_count=client_count,
        )
    
    def _resolve_single_asset(self, requirement: AssetRequirement) -> ResolvedAsset:
        """Resolve a single asset to a path."""
        
        # 1. If client-provided, keep as-is
        if requirement.source_strategy == SourceStrategy.CLIENT_PROVIDED:
            return ResolvedAsset(
                requirement=requirement,
                resolution_path=ResolutionPath.CLIENT,
                reasoning="Client-provided asset",
                confidence=1.0,
            )
        
        # 2. Icons and logos → Icon libraries
        if requirement.asset_type in self.icon_types:
            return ResolvedAsset(
                requirement=requirement,
                resolution_path=ResolutionPath.ICON_CSS,
                reasoning=f"Icon/Logo type: {requirement.asset_type.value}",
                confidence=0.95,
                library_name=self._select_icon_library(requirement),
            )
        
        # 3. Generation required → Generate
        if requirement.generation_required or requirement.source_strategy == SourceStrategy.GENERATE:
            return ResolvedAsset(
                requirement=requirement,
                resolution_path=ResolutionPath.GENERATE,
                reasoning="Explicit generation requirement or strategy",
                confidence=0.95,
                generation_prompt=requirement.prompt,
            )
        
        # 4. High-priority generatable types → Generate
        if (requirement.asset_type in self.generatable_types and 
            requirement.priority in [AssetPriority.HIGH, AssetPriority.CRITICAL]):
            return ResolvedAsset(
                requirement=requirement,
                resolution_path=ResolutionPath.GENERATE,
                reasoning=f"High-priority {requirement.asset_type.value}",
                confidence=0.85,
                generation_prompt=requirement.prompt,
            )
        
        # 5. Medium priority generatable → Try STOCK first, fallback to GENERATE
        if requirement.asset_type in self.generatable_types:
            keywords = self._extract_search_keywords(requirement)
            if keywords:
                return ResolvedAsset(
                    requirement=requirement,
                    resolution_path=ResolutionPath.STOCK,
                    reasoning=f"Medium-priority {requirement.asset_type.value}, attempt STOCK search first",
                    confidence=0.70,
                    search_keywords=keywords,
                )
            else:
                # No good keywords for search → Generate instead
                return ResolvedAsset(
                    requirement=requirement,
                    resolution_path=ResolutionPath.GENERATE,
                    reasoning="Insufficient search keywords, fallback to generation",
                    confidence=0.75,
                    generation_prompt=requirement.prompt,
                )
        
        # 6. Fallback: Generate
        return ResolvedAsset(
            requirement=requirement,
            resolution_path=ResolutionPath.GENERATE,
            reasoning="Default fallback to generation",
            confidence=0.60,
            generation_prompt=requirement.prompt,
        )
    
    def _select_icon_library(self, requirement: AssetRequirement) -> str:
        """Select appropriate icon library based on asset details."""
        # Could expand with more sophisticated logic
        if "brand" in requirement.purpose.lower():
            return "brand_icons"
        elif "social" in requirement.purpose.lower():
            return "social_icons"
        else:
            return "feather_icons"  # Default: Feather Icons
    
    def _extract_search_keywords(self, requirement: AssetRequirement) -> List[str]:
        """Extract keywords for stock search from asset requirement."""
        keywords = []
        
        # Add style keywords
        if requirement.style_keywords:
            keywords.extend(requirement.style_keywords)
        
        # Add purpose as keyword
        if requirement.purpose:
            # Simple tokenization
            purpose_keywords = [
                w.strip().lower() 
                for w in requirement.purpose.split() 
                if len(w.strip()) > 3
            ]
            keywords.extend(purpose_keywords)
        
        # Add asset type
        keywords.append(requirement.asset_type.value.replace("_", " "))
        
        # Add page/section context
        if requirement.page_name:
            keywords.append(requirement.page_name.lower().replace("_", " "))
        
        return list(dict.fromkeys(keywords))[:5]  # Deduplicate and limit to 5
