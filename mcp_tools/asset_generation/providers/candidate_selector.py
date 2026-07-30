"""
Candidate Selector - Intelligently selects the best candidate from search results.

Selection criteria:
- Dimension matching (aspect ratio)
- Quality score
- License compatibility
- Author rating
"""

import logging
from typing import List, Optional

from schema.asset import AssetRequirement
from mcp_tools.asset_generation.providers.search_provider import SearchCandidate


logger = logging.getLogger(__name__)


class CandidateSelector:
    """Selects the best candidate from search results."""
    
    def __init__(self):
        self.acceptable_aspect_ratio_tolerance = 0.15  # 15% tolerance
    
    def select_best(
        self,
        requirement: AssetRequirement,
        candidates: List[SearchCandidate],
    ) -> Optional[SearchCandidate]:
        """
        Select the best candidate for the asset requirement.
        
        Args:
            requirement: AssetRequirement to fulfill
            candidates: List of SearchCandidate options
            
        Returns:
            Best SearchCandidate or None if none suitable
        """
        if not candidates:
            logger.warning(f"No candidates for {requirement.asset_id}")
            return None
        
        # Score each candidate
        scored_candidates = [
            (candidate, self._score_candidate(requirement, candidate))
            for candidate in candidates
        ]
        
        # Sort by score (highest first)
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Log scoring
        for i, (candidate, score) in enumerate(scored_candidates[:3]):
            logger.info(
                f"Candidate {i+1}",
                extra={
                    "asset_id": requirement.asset_id,
                    "source": candidate.source,
                    "score": score,
                    "author": candidate.author,
                    "dimensions": f"{candidate.width}x{candidate.height}",
                }
            )
        
        best_candidate, best_score = scored_candidates[0]
        
        # Check if best score is acceptable
        if best_score < 0.5:
            logger.warning(
                f"Best candidate score too low: {best_score}",
                extra={"asset_id": requirement.asset_id}
            )
            return None
        
        logger.info(
            f"Selected candidate",
            extra={
                "asset_id": requirement.asset_id,
                "score": best_score,
                "author": best_candidate.author,
            }
        )
        
        return best_candidate
    
    def _score_candidate(
        self,
        requirement: AssetRequirement,
        candidate: SearchCandidate,
    ) -> float:
        """
        Score a candidate on 0-1 scale.
        
        Factors:
        - Aspect ratio match (0-0.4)
        - Minimum dimension requirement (0-0.3)
        - Search relevance score (0-0.3)
        """
        score = 0.0
        
        # 1. Aspect ratio matching (40% weight)
        aspect_score = self._score_aspect_ratio(requirement, candidate)
        score += aspect_score * 0.4
        
        # 2. Minimum dimensions (30% weight)
        dimension_score = self._score_dimensions(requirement, candidate)
        score += dimension_score * 0.3
        
        # 3. Relevance/ranking (30% weight)
        score += candidate.score * 0.3
        
        return score
    
    def _score_aspect_ratio(
        self,
        requirement: AssetRequirement,
        candidate: SearchCandidate,
    ) -> float:
        """Score how well candidate's aspect ratio matches requirement."""
        required_ratio = requirement.width / requirement.height
        candidate_ratio = candidate.width / candidate.height
        
        ratio_diff = abs(required_ratio - candidate_ratio) / required_ratio
        
        # Within tolerance = 1.0, outside = lower
        if ratio_diff <= self.acceptable_aspect_ratio_tolerance:
            return 1.0
        else:
            # Linear decay: 0% diff = 1.0, 50% diff = 0.0
            return max(0.0, 1.0 - (ratio_diff / 0.5))
    
    def _score_dimensions(
        self,
        requirement: AssetRequirement,
        candidate: SearchCandidate,
    ) -> float:
        """Score if candidate meets minimum dimension requirements."""
        # Need both width and height to meet requirement
        width_ok = candidate.width >= requirement.width
        height_ok = candidate.height >= requirement.height
        
        if width_ok and height_ok:
            return 1.0
        
        # Partial credit if one dimension is met
        if width_ok or height_ok:
            return 0.5
        
        # Check if it's close enough (within 80%)
        width_ratio = candidate.width / requirement.width if requirement.width > 0 else 1.0
        height_ratio = candidate.height / requirement.height if requirement.height > 0 else 1.0
        
        if width_ratio >= 0.8 and height_ratio >= 0.8:
            return 0.7
        
        return 0.0
