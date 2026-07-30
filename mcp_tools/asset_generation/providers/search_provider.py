"""
Stock Asset Search Provider - Searches free image APIs for assets.

Supports:
- Unsplash API (requires free API key)
- Pexels API (not implemented)
- Pixabay API (not implemented)

Returns candidate images that match search criteria.
"""

import logging
import aiohttp
from pydantic import BaseModel
import os
from typing import List
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()  # Load environment variables from .env file



class SearchCandidate(BaseModel):
    """A candidate image from search results."""
    
    candidate_id: str
    source: str  # unsplash, pexels, pixabay
    source_url: str  # Direct image URL
    thumbnail_url: str
    title: str
    author: str
    width: int
    height: int
    download_url: str
    license: str  # License type (CC0, etc.)
    score: float = 0.0  # Relevance score 0-1


class SearchQuery(BaseModel):
    """Search query parameters."""
    
    keywords: List[str]
    width_min: int = 800
    height_min: int = 600
    orientation: str = "landscape"  # landscape, portrait, any
    max_results: int = 10




class SearchProvider:
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")
    
    async def search(
        self,
        query: SearchQuery,
        provider: str = "unsplash"
    ) -> List[SearchCandidate]:
        """
        Search for images matching the query.
        
        Args:
            query: SearchQuery with keywords and parameters
            provider: Which API to use (unsplash, pexels, pixabay)
            
        Returns:
            List of SearchCandidate results
        """
        if provider == "unsplash":
            return await self._search_unsplash(query)
        elif provider == "pexels":
            return await self._search_pexels(query)
        elif provider == "pixabay":
            return await self._search_pixabay(query)
        else:
            logger.warning(f"Unknown provider: {provider}")
            return []
    
    async def _search_unsplash(self, query: SearchQuery) -> List[SearchCandidate]:
        """Search Unsplash API."""

        if not self.unsplash_key:
            logger.error("UNSPLASH_ACCESS_KEY not configured")
            return []
        try:
            search_term = " ".join(query.keywords)  # First 3 keywords
            
            url = "https://api.unsplash.com/search/photos"
            params = {
                "query": search_term,
                "per_page": min(query.max_results, 30),
            }

            if query.orientation in {"landscape", "portrait", "squarish"}:
                params["orientation"] = query.orientation
            
            headers = {
                "Authorization": f"Client-ID {self.unsplash_key}",
                "Accept-Version": "v1",
                "User-Agent": "AssetSearchProvider/1.0",
            }

            async with aiohttp.ClientSession(
                timeout=self.timeout,
                headers=headers,
            ) as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.warning(f"Unsplash search failed: {response.status}")
                        return []
                    
                    data = await response.json()
                    results = data.get("results", [])
                    
                    candidates = []
                    for i, result in enumerate(results):
                        width = result["width"]
                        height = result["height"]

                        if width < query.width_min or height < query.height_min:
                            continue
                        try:
                            candidate = SearchCandidate(
                                candidate_id=f"unsplash_{result['id']}",
                                source="unsplash",
                                source_url=result["urls"]["regular"],
                                thumbnail_url=result["urls"]["thumb"],
                                title=(
                                    result.get("description")
                                    or result.get("alt_description")
                                    or "Unsplash Image"
                                ),
                                author=result["user"]["name"],
                                width=width,
                                height=height,
                                download_url=result["urls"]["full"],
                                license="Unsplash License",
                                score=1.0 - (i * 0.1),  # Decrease score by rank
                            )
                            candidates.append(candidate)
                        except (KeyError, TypeError) as e:
                            logger.warning(f"Failed to parse Unsplash result: {e}")
                            continue
                    
                    logger.info(
                        "Unsplash search results",
                        extra={"query": search_term, "candidates": len(candidates)}
                    )
                    return candidates
        
        except Exception as e:
            logger.error(f"Unsplash search error: {e}")
            return []
    
    async def _search_pexels(self, query: SearchQuery) -> List[SearchCandidate]:
        """Search Pexels API (free alternative)."""
        # Pexels requires an API key, skip for now
        logger.info("Pexels provider not implemented (requires API key)")
        return []
    
    async def _search_pixabay(self, query: SearchQuery) -> List[SearchCandidate]:
        """Search Pixabay API (free alternative)."""
        # Pixabay requires an API key, skip for now
        logger.info("Pixabay provider not implemented (requires API key)")
        return []







async def main():
    provider = SearchProvider()

    query = SearchQuery(
        keywords=[
            "modern",
            "luxury",
            "living room",
            "interior"
        ],
        width_min=1000,
        height_min=800,
        orientation="landscape",
        max_results=5,
    )

    results = await provider.search(query)

    print(f"\nFound {len(results)} candidates\n")

    for i, candidate in enumerate(results, start=1):
        print("=" * 60)
        print(f"Result #{i}")
        print(f"ID: {candidate.candidate_id}")
        print(f"Source: {candidate.source}")
        print(f"Title: {candidate.title}")
        print(f"Author: {candidate.author}")
        print(f"Resolution: {candidate.width} x {candidate.height}")
        print(f"Score: {candidate.score:.2f}")
        print(f"Image URL: {candidate.source_url}")
        print(f"Download URL: {candidate.download_url}")
        print()


if __name__ == "__main__":
    asyncio.run(main())





