"""
Asset Downloader - Downloads selected candidate images.

Handles:
- Downloading from direct URLs
- Error handling and retries
- File storage
- Verification (file size, format)
"""

import logging
import aiohttp
from typing import Optional

from schema.asset_gen import GeneratedAsset, GenerationStatus
from mcp_tools.asset_generation.providers.search_provider import SearchCandidate
from mcp_tools.asset_generation.storage.asset_storage import AssetStorage


logger = logging.getLogger(__name__)


class AssetDownloader:
    """Download and save candidate images."""
    
    def __init__(self, storage: Optional[AssetStorage] = None):
        self.storage = storage or AssetStorage()
        self.timeout = aiohttp.ClientTimeout(total=60)
        self.max_retries = 3
        self.min_file_size = 1000  # 1KB minimum
    
    async def download(
        self,
        asset_id: str,
        candidate: SearchCandidate,
        output_filename: str,
        asset_type,
        width: int,
        height: int,
    ) -> GeneratedAsset:
        """
        Download a candidate image.
        
        Args:
            asset_id: Asset identifier
            candidate: SearchCandidate to download
            output_filename: Where to save the file
            asset_type: AssetType enum value
            width: Expected width
            height: Expected height
            
        Returns:
            GeneratedAsset with result
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Downloading candidate (attempt {attempt + 1}/{self.max_retries})",
                    extra={
                        "asset_id": asset_id,
                        "source": candidate.source,
                        "url": candidate.source_url,
                    }
                )
                
                # Download image bytes
                image_bytes = await self._fetch_image(candidate.source_url)
                
                # Verify file size
                if len(image_bytes) < self.min_file_size:
                    logger.warning(
                        f"Downloaded file too small: {len(image_bytes)} bytes",
                        extra={"asset_id": asset_id}
                    )
                    if attempt < self.max_retries - 1:
                        continue
                    else:
                        raise ValueError("Downloaded file too small")
                
                # Save to storage
                file_path = await self.storage.save_image(image_bytes, output_filename)
                
                logger.info(
                    "Asset downloaded successfully",
                    extra={
                        "asset_id": asset_id,
                        "file_path": file_path,
                        "file_size": len(image_bytes),
                    }
                )
                
                # Return success
                return GeneratedAsset(
                    asset_id=asset_id,
                    asset_type=asset_type,
                    file_path=file_path,
                    provider=candidate.source,
                    status=GenerationStatus.SUCCESS,
                    width=width,
                    height=height,
                    created_at=self._timestamp(),
                    provider_asset_url=candidate.source_url,
                )
            
            except Exception as e:
                logger.warning(
                    f"Download attempt {attempt + 1} failed: {e}",
                    extra={"asset_id": asset_id}
                )
                if attempt == self.max_retries - 1:
                    # Final attempt failed
                    logger.error(
                        "All download attempts failed",
                        extra={"asset_id": asset_id, "error": str(e)}
                    )
                    return self._failed_asset(asset_id, asset_type, e, width, height)
        
        # Should not reach here
        return self._failed_asset(
            asset_id,
            asset_type,
            Exception("Unknown download failure"),
            width,
            height
        )
    
    async def _fetch_image(self, url: str) -> bytes:
        """Fetch image bytes from URL."""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url) as response:
                if response.status >= 400:
                    raise RuntimeError(f"HTTP {response.status}: {url}")
                
                content_type = response.headers.get("content-type", "")
                if not content_type.startswith("image/"):
                    raise ValueError(f"Invalid content-type: {content_type}")
                
                image_bytes = await response.read()
                return image_bytes
    
    def _failed_asset(
        self,
        asset_id: str,
        asset_type,
        error: Exception,
        width: int,
        height: int,
    ) -> GeneratedAsset:
        """Create a failed asset entry."""
        return GeneratedAsset(
            asset_id=asset_id,
            asset_type=asset_type,
            file_path="",
            provider="stock_search",
            status=GenerationStatus.FAILED,
            width=width,
            height=height,
            error=str(error),
            created_at=self._timestamp(),
            provider_asset_url=None,
        )
    
    def _timestamp(self) -> str:
        """Get current UTC timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
