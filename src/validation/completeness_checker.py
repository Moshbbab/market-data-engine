"""
Completeness Checker
====================

Measures how complete property records are across a defined set of key fields.

Completeness is computed as:

    completeness = (non-null key-field values) / (total key-field slots) × 100

Author: Hemmah Valuation Systems
License: MIT
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Fields considered "key" for completeness scoring
_KEY_FIELDS: List[str] = [
    "address",
    "price",
    "sqft",
    "bedrooms",
    "bathrooms",
    "year_built",
    "property_type",
    "status",
    "lot_size",
    "list_date",
]


class CompletenessChecker:
    """
    Check and score the completeness of property records.

    Args:
        key_fields: Fields to include in the completeness calculation.
                    Defaults to the standard real-estate key fields.
        threshold:  Minimum completeness percentage (0-100) for a record
                    to be considered "complete". Default is 70.
    """

    def __init__(
        self,
        key_fields: Optional[List[str]] = None,
        threshold: float = 70.0,
    ) -> None:
        self.key_fields = key_fields or _KEY_FIELDS
        self.threshold = threshold
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, records: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        Annotate records with their completeness scores and produce a summary.

        Each record gets a ``_completeness_score`` (0–100) and a
        ``_missing_key_fields`` list.

        Args:
            records: Validated property records.

        Returns:
            Tuple of (annotated records, completeness summary dict).
        """
        scores: List[float] = []
        complete_count = 0

        for record in records:
            score, missing = self._score_record(record)
            record["_completeness_score"] = round(score, 2)
            record["_missing_key_fields"] = missing
            scores.append(score)
            if score >= self.threshold:
                complete_count += 1

        avg_score = sum(scores) / len(scores) if scores else 0.0
        summary = {
            "total_records": len(records),
            "complete_records": complete_count,
            "incomplete_records": len(records) - complete_count,
            "average_completeness": round(avg_score, 2),
            "threshold": self.threshold,
        }

        self.logger.info(
            "Completeness check: avg %.1f%%, %d/%d records meet threshold",
            avg_score,
            complete_count,
            len(records),
        )
        return records, summary

    def score_record(self, record: Dict) -> float:
        """Return the completeness score (0-100) for a single record."""
        score, _ = self._score_record(record)
        return score

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _score_record(self, record: Dict) -> Tuple[float, List[str]]:
        missing: List[str] = []
        present = 0

        for field in self.key_fields:
            value = record.get(field)
            if value is not None and value != "":
                present += 1
            else:
                missing.append(field)

        total = len(self.key_fields)
        score = (present / total * 100) if total > 0 else 0.0
        return score, missing
