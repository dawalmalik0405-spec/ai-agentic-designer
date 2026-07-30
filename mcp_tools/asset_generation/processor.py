"""
Asset Processor - Executes asset resolution paths and produces final assets.

Handles:
- GENERATE: Image generation via Pollinations
- STOCK: Asset search/download (Unsplash integration)
- ICON_CSS: Icon/CSS library lookup (Feather, Lucide, Material, Heroicons, etc.)
- CLIENT: Pass-through for client assets
- FALLBACK: Retry with alternative paths on failure
"""

import logging
import time
import os
from datetime import datetime, timezone
from typing import List

from schema.asset import AssetType
from schema.asset_resolver import ResolvedAsset, ResolutionPath
from schema.asset_processor import (
    ProcessedAsset,
    ProcessingPhase,
    ProcessorOutput,
)
from schema.asset_gen import GeneratedAsset, GenerationStatus
from mcp_tools.asset_generation.executor import AssetExecutor


logger = logging.getLogger(__name__)


class AssetProcessor:
    """Processes resolved assets through their assigned paths."""
    
    def __init__(self):
        self.executor = AssetExecutor()
        self.processed_assets: List[ProcessedAsset] = []
    
    async def process(self, resolver_output) -> ProcessorOutput:
        """
        Process all resolved assets through their paths.
        
        Args:
            resolver_output: ResolverOutput from AssetResolver
            
        Returns:
            ProcessorOutput with processed assets
        """
        await self.executor.connect()
        
        try:
            self.processed_assets = []
            total_file_size = 0
            processing_times = []
            
            for resolved_asset in resolver_output.resolved_assets:
                start_time = time.time()
                
                processed = await self._process_asset(resolved_asset)
                self.processed_assets.append(processed)
                
                processing_time_ms = (time.time() - start_time) * 1000
                processed.processing_time_ms = processing_time_ms
                processing_times.append(processing_time_ms)
                
                if processed.file_size:
                    total_file_size += processed.file_size
                
                logger.info(
                    "Asset processed",
                    extra={
                        "asset_id": processed.asset_id,
                        "phase": processed.processing_phase.value,
                        "time_ms": processing_time_ms,
                    }
                )
            
            # Calculate statistics
            successful = sum(
                1 for p in self.processed_assets 
                if p.processing_phase == ProcessingPhase.VALIDATED
            )
            failed = sum(
                1 for p in self.processed_assets 
                if p.processing_phase == ProcessingPhase.FAILED
            )
            skipped = sum(
                1 for p in self.processed_assets 
                if p.processing_phase == ProcessingPhase.RESOLVED
            )
            
            avg_time = sum(processing_times) / len(processing_times) if processing_times else 0
            
            return ProcessorOutput(
                total_assets=len(self.processed_assets),
                processed_assets=self.processed_assets,
                successful=successful,
                failed=failed,
                skipped=skipped,
                total_file_size_bytes=total_file_size,
                average_processing_time_ms=avg_time,
            )
        
        finally:
            await self.executor.close()
    
    async def _process_asset(self, resolved_asset: ResolvedAsset) -> ProcessedAsset:
        """Process a single resolved asset through its path."""
        
        processed = ProcessedAsset(
            asset_id=resolved_asset.requirement.asset_id,
            asset_type=resolved_asset.requirement.asset_type,
            processing_phase=ProcessingPhase.RESOLVED,
            resolution_path=resolved_asset.resolution_path.value,
        )
        
        try:
            # Route to appropriate handler
            if resolved_asset.resolution_path == ResolutionPath.GENERATE:
                await self._process_generate(resolved_asset, processed)
            
            elif resolved_asset.resolution_path == ResolutionPath.STOCK:
                await self._process_stock(resolved_asset, processed)
            
            elif resolved_asset.resolution_path == ResolutionPath.ICON_CSS:
                await self._process_icon_css(resolved_asset, processed)
            
            elif resolved_asset.resolution_path == ResolutionPath.CLIENT:
                await self._process_client(resolved_asset, processed)
            
            # Validate if we have an asset
            if processed.generated_asset and processed.generated_asset.status == GenerationStatus.SUCCESS:
                processed.processing_phase = ProcessingPhase.VALIDATED
                processed.validation_passed = True
                processed.file_path = processed.generated_asset.file_path
                
                # Get file size if available
                if processed.file_path and os.path.exists(processed.file_path):
                    processed.file_size = os.path.getsize(processed.file_path)
            
            return processed
        
        except Exception as e:
            logger.error(
                "Asset processing error",
                extra={
                    "asset_id": processed.asset_id,
                    "error": str(e),
                }
            )
            processed.processing_phase = ProcessingPhase.FAILED
            processed.validation_errors.append(str(e))
            return processed
    
    async def _process_generate(self, resolved_asset: ResolvedAsset, processed: ProcessedAsset):
        """Process GENERATE path - use image generation."""
        processed.processing_phase = ProcessingPhase.ATTEMPTING_PATH
        processed.attempted_paths.append("generate")
        
        requirement = resolved_asset.requirement
        
        try:
            # Use the existing executor to generate the image
            results = await self.executor.execute_asset(requirement)
            if results:
                processed.generated_asset = results[0]  # Take first result
                processed.created_at = self._timestamp()
            
        except Exception as e:
            logger.warning(f"Generation failed for {requirement.asset_id}: {e}")
            processed.generated_asset = self.executor.failed_asset(requirement, e)
            
            # Try fallback: STOCK
            if resolved_asset.confidence < 0.9:  # Only fallback if not high confidence
                logger.info(f"Attempting fallback: STOCK for {requirement.asset_id}")
                await self._process_stock(resolved_asset, processed)
    
    async def _process_stock(self, resolved_asset: ResolvedAsset, processed: ProcessedAsset):
        """Process STOCK path - search and download from existing sources."""
        processed.processing_phase = ProcessingPhase.ATTEMPTING_PATH
        processed.attempted_paths.append("stock")
        
        requirement = resolved_asset.requirement
        
        try:
            # Import stock path components
            from mcp_tools.asset_generation.providers.search_provider import (
                SearchProvider,
                SearchQuery,
            )
            from mcp_tools.asset_generation.providers.candidate_selector import (
                CandidateSelector,
            )
            from mcp_tools.asset_generation.providers.asset_downloader import (
                AssetDownloader,
            )
            
            # Step 1: Search
            logger.info(
                "Searching stock images",
                extra={
                    "asset_id": requirement.asset_id,
                    "keywords": resolved_asset.search_keywords,
                }
            )
            
            search_provider = SearchProvider()
            search_query = SearchQuery(
                keywords=resolved_asset.search_keywords or [requirement.purpose],
                width_min=requirement.width,
                height_min=requirement.height,
                orientation="landscape",
                max_results=10,
            )
            
            candidates = await search_provider.search(search_query, provider="unsplash")
            
            if not candidates:
                logger.warning(f"No candidates found for {requirement.asset_id}")
                # Fallback to generation
                await self._process_generate(resolved_asset, processed)
                return
            
            # Step 2: Select best candidate
            selector = CandidateSelector()
            best_candidate = selector.select_best(requirement, candidates)
            
            if not best_candidate:
                logger.warning(f"No suitable candidate for {requirement.asset_id}")
                # Fallback to generation
                await self._process_generate(resolved_asset, processed)
                return
            
            # Step 3: Download
            downloader = AssetDownloader(self.executor.storage)
            result = await downloader.download(
                asset_id=requirement.asset_id,
                candidate=best_candidate,
                output_filename=requirement.output_filename,
                asset_type=requirement.asset_type,
                width=best_candidate.width,
                height=best_candidate.height,
            )
            
            processed.generated_asset = result
            processed.created_at = self._timestamp()
            
            if result.status != GenerationStatus.SUCCESS:
                logger.warning(f"Stock download failed, falling back to generation")
                await self._process_generate(resolved_asset, processed)
        
        except Exception as e:
            logger.warning(f"Stock path error for {requirement.asset_id}: {e}")
            # Fallback to generation
            await self._process_generate(resolved_asset, processed)
    
    async def _process_icon_css(self, resolved_asset: ResolvedAsset, processed: ProcessedAsset):
        """Process ICON_CSS path - fetch from icon libraries."""
        processed.processing_phase = ProcessingPhase.ATTEMPTING_PATH
        processed.attempted_paths.append("icon_css")
        
        requirement = resolved_asset.requirement
        library_name = resolved_asset.library_name or "feather_icons"
        
        try:
            # Import icon/CSS providers
            from mcp_tools.asset_generation.providers.icon_provider import (
                IconLibraryProvider,
                IconLibrary,
            )
            from mcp_tools.asset_generation.providers.css_provider import (
                CSSLibraryProvider,
                CSSLibrary,
            )
            
            # Check if it's an icon or CSS font
            if requirement.asset_type == AssetType.ICON:
                # Use icon provider
                logger.info(
                    f"Fetching icon for {requirement.asset_id}",
                    extra={"library": library_name}
                )
                
                icon_provider = IconLibraryProvider()
                
                # Map library name to IconLibrary enum
                library_map = {
                    "feather_icons": IconLibrary.FEATHER,
                    "lucide_icons": IconLibrary.LUCIDE,
                    "material_icons": IconLibrary.MATERIAL,
                    "phosphor_icons": IconLibrary.PHOSPHOR,
                }
                
                selected_library = library_map.get(library_name, IconLibrary.FEATHER)
                
                # Extract icon name from purpose or asset_id
                icon_name = requirement.purpose.lower().replace(" ", "_")
                
                icon_data = icon_provider.get_icon_url(icon_name, selected_library)
                
                if icon_data:
                    # Create asset entry for icon
                    processed.generated_asset = GeneratedAsset(
                        asset_id=requirement.asset_id,
                        asset_type=requirement.asset_type,
                        file_path=icon_data.svg_url,
                        provider=f"icon_library_{selected_library.value}",
                        status=GenerationStatus.SUCCESS,
                        width=24,
                        height=24,
                        created_at=self._timestamp(),
                        provider_asset_url=icon_data.svg_url,
                    )
                    processed.created_at = self._timestamp()
                    logger.info(f"Icon fetched: {icon_name}")
                else:
                    logger.warning(f"Icon not found: {icon_name}")
                    processed.generated_asset = self.executor.failed_asset(
                        requirement,
                        Exception(f"Icon not found: {icon_name}")
                    )
            
            elif requirement.asset_type == AssetType.LOGO:
                # Use CSS library provider (logo fonts)
                logger.info(
                    f"Fetching logo from CSS library for {requirement.asset_id}",
                    extra={"library": library_name}
                )
                
                css_provider = CSSLibraryProvider()
                
                # Map library name to CSSLibrary enum
                library_map = {
                    "bootstrap_icons": CSSLibrary.BOOTSTRAP_ICONS,
                    "heroicons": CSSLibrary.HEROICONS,
                    "font_awesome": CSSLibrary.FONT_AWESOME,
                    "ionicons": CSSLibrary.IONICONS,
                }
                
                selected_library = library_map.get(library_name, CSSLibrary.HEROICONS)
                
                css_asset = css_provider.get_library_css(selected_library)
                
                if css_asset:
                    processed.generated_asset = GeneratedAsset(
                        asset_id=requirement.asset_id,
                        asset_type=requirement.asset_type,
                        file_path=css_asset.cdn_url,
                        provider=f"css_library_{selected_library.value}",
                        status=GenerationStatus.SUCCESS,
                        width=24,
                        height=24,
                        created_at=self._timestamp(),
                        provider_asset_url=css_asset.cdn_url,
                    )
                    processed.created_at = self._timestamp()
                    logger.info(f"CSS library fetched: {css_asset.name}")
                else:
                    logger.warning(f"CSS library not found: {library_name}")
                    processed.generated_asset = self.executor.failed_asset(
                        requirement,
                        Exception(f"CSS library not found: {library_name}")
                    )
            else:
                logger.warning(f"Icon/CSS path used for unsupported type: {requirement.asset_type}")
                processed.generated_asset = self.executor.failed_asset(
                    requirement,
                    Exception(f"Unsupported asset type for ICON_CSS: {requirement.asset_type}")
                )
        
        except Exception as e:
            logger.error(f"Icon/CSS path error for {requirement.asset_id}: {e}")
            processed.generated_asset = self.executor.failed_asset(requirement, e)
    
    async def _process_client(self, resolved_asset: ResolvedAsset, processed: ProcessedAsset):
        """Process CLIENT path - client-provided assets."""
        processed.processing_phase = ProcessingPhase.ATTEMPTING_PATH
        processed.attempted_paths.append("client")
        
        requirement = resolved_asset.requirement
        
        # Check if source file exists
        if requirement.source_output_filename and os.path.exists(requirement.source_output_filename):
            processed.generated_asset = GeneratedAsset(
                asset_id=requirement.asset_id,
                asset_type=requirement.asset_type,
                file_path=requirement.source_output_filename,
                provider="client",
                status=GenerationStatus.SUCCESS,
                width=requirement.width,
                height=requirement.height,
                created_at=self._timestamp(),
                provider_asset_url=None,
            )
            processed.processing_phase = ProcessingPhase.DOWNLOADED
        else:
            logger.warning(f"Client asset not found: {requirement.source_output_filename}")
            processed.processing_phase = ProcessingPhase.FAILED
            processed.validation_errors.append("Client asset source file not found")
    
    def _timestamp(self) -> str:
        """Get current UTC timestamp."""
        return datetime.now(timezone.utc).isoformat()
