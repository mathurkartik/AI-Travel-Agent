"""
User feedback collection and aggregation.
Stores feedback as JSONL and provides summary statistics.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class FeedbackRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=200)
    plan_id: str = Field(..., min_length=1, max_length=200)
    rating: int = Field(..., ge=1, le=5)
    categories: List[str] = Field(default_factory=list)
    comment: Optional[str] = Field(default=None, max_length=2000)
    would_use_plan: Optional[bool] = None

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: List[str]) -> List[str]:
        allowed = {
            "accurate_days", "good_activities", "realistic_budget",
            "good_route", "good_insights", "good_neighborhoods",
            "good_pacing", "too_rushed", "too_slow",
        }
        return [c for c in v if c in allowed]


class FeedbackStore:
    def __init__(self, log_path: Optional[Path] = None):
        backend_dir = Path(__file__).resolve().parent.parent.parent
        self._log_path = log_path or backend_dir / "data" / "feedback_log.jsonl"

    def save(self, feedback: FeedbackRequest, variant_info: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        entry = {
            "session_id": feedback.session_id,
            "plan_id": feedback.plan_id,
            "rating": feedback.rating,
            "categories": feedback.categories,
            "comment": feedback.comment,
            "would_use_plan": feedback.would_use_plan,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if variant_info:
            entry["variants"] = variant_info

        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as exc:
            logger.error("Failed to save feedback: %s", exc)
            raise

        return entry

    def get_summary(self) -> Dict[str, Any]:
        entries = self._read_all()
        if not entries:
            return {
                "count": 0,
                "average_rating": 0.0,
                "category_counts": {},
                "would_use_rate": 0.0,
                "per_variant": {},
            }

        ratings = [e["rating"] for e in entries]
        category_counts: Dict[str, int] = {}
        for e in entries:
            for cat in e.get("categories", []):
                category_counts[cat] = category_counts.get(cat, 0) + 1

        would_use = [e["would_use_plan"] for e in entries if e.get("would_use_plan") is not None]
        would_use_rate = sum(1 for w in would_use if w) / len(would_use) if would_use else 0.0

        per_variant = self._aggregate_by_variant(entries)

        return {
            "count": len(entries),
            "average_rating": round(sum(ratings) / len(ratings), 2),
            "rating_distribution": {str(r): ratings.count(r) for r in range(1, 6)},
            "category_counts": category_counts,
            "would_use_rate": round(would_use_rate, 2),
            "per_variant": per_variant,
        }

    def _aggregate_by_variant(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        variant_data: Dict[str, List[int]] = {}
        for e in entries:
            variants = e.get("variants", {})
            for exp_name, variant_name in variants.items():
                key = f"{exp_name}:{variant_name}"
                if key not in variant_data:
                    variant_data[key] = []
                variant_data[key].append(e["rating"])

        result: Dict[str, Any] = {}
        for key, ratings in variant_data.items():
            result[key] = {
                "count": len(ratings),
                "average_rating": round(sum(ratings) / len(ratings), 2),
            }
        return result

    def _read_all(self) -> List[Dict[str, Any]]:
        if not self._log_path.exists():
            return []
        entries: List[Dict[str, Any]] = []
        try:
            with open(self._log_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        except Exception as exc:
            logger.warning("Failed to read feedback log: %s", exc)
        return entries


_store: Optional[FeedbackStore] = None


def get_feedback_store() -> FeedbackStore:
    global _store
    if _store is None:
        _store = FeedbackStore()
    return _store
