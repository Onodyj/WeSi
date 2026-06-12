"""SiteIQ - Website Analysis Platform"""

from .recommendations import RecommendationEngine
from .scoring import SiteIQScorer, score_to_grade, score_to_label

__version__ = '3.0.0'
__name_human__ = 'SiteIQ'

__all__ = ["RecommendationEngine", "SiteIQScorer", "score_to_grade", "score_to_label"]
