"""
Quality Scorer
==============

Aggregates data-quality dimensions into a single composite score (0–100).

Dimensions and weights:
  - Completeness  (40%) – average completeness score across all records
  - Validity      (30%) – % of records that pass schema + business rules
  - Uniqueness    (20%) – % of records that are not duplicates
  - Timeliness    (10%) – % of records with a list_date within max_age_days

Author: Hemmah Valuation Systems
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Default weights (must sum to 1.0)
_WEIGHTS: Dict[str, float] = {
    "completeness": 0.40,
    "validity": 0.30,
    "uniqueness": 0.20,
    "timeliness": 0.10,
}


@dataclass
class QualityReport:
    """Detailed quality scoring report."""

    total_records: int
    completeness_score: float    # 0-100
    validity_score: float        # 0-100
    uniqueness_score: float      # 0-100
    timeliness_score: float      # 0-100
    composite_score: float       # 0-100 (weighted average)
    dimension_weights: Dict[str, float] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)

    @property
    def grade(self) -> str:
        """Letter grade based on composite score."""
        if self.composite_score >= 90:
            return "A"
        if self.composite_score >= 80:
            return "B"
        if self.composite_score >= 70:
            return "C"
        if self.composite_score >= 60:
            return "D"
        return "F"


class QualityScorer:
    """
    Compute a composite data-quality score for a batch of records.

    Args:
        weights:       Override the default dimension weights. Must sum to 1.0.
        max_age_days:  Records older than this are considered stale (timeliness).
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        max_age_days: int = 30,
    ) -> None:
        self.weights = weights or _WEIGHTS
        self.max_age_days = max_age_days
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(
        self,
        records: List[Dict],
        duplicates_removed: int = 0,
        original_count: Optional[int] = None,
    ) -> QualityReport:
        """
        Compute a quality report for *records*.

        Args:
            records:           Cleaned and validated records (with completeness
                               scores already attached by CompletenessChecker).
            duplicates_removed: Count of duplicates removed during cleaning.
            original_count:    Original record count before deduplication
                               (used for uniqueness calculation).

        Returns:
            :class:`QualityReport`
        """
        if not records:
            return QualityReport(
                total_records=0,
                completeness_score=0.0,
                validity_score=0.0,
                uniqueness_score=0.0,
                timeliness_score=0.0,
                composite_score=0.0,
                dimension_weights=self.weights,
                issues=["No records to score."],
            )

        completeness = self._completeness_score(records)
        validity = self._validity_score(records)
        uniqueness = self._uniqueness_score(records, duplicates_removed, original_count)
        timeliness = self._timeliness_score(records)

        composite = (
            completeness * self.weights.get("completeness", 0.40)
            + validity * self.weights.get("validity", 0.30)
            + uniqueness * self.weights.get("uniqueness", 0.20)
            + timeliness * self.weights.get("timeliness", 0.10)
        )

        issues = self._identify_issues(completeness, validity, uniqueness, timeliness)

        report = QualityReport(
            total_records=len(records),
            completeness_score=round(completeness, 2),
            validity_score=round(validity, 2),
            uniqueness_score=round(uniqueness, 2),
            timeliness_score=round(timeliness, 2),
            composite_score=round(composite, 2),
            dimension_weights=self.weights,
            issues=issues,
        )

        self.logger.info(
            "Quality score: %.1f/100 (grade %s) – completeness=%.1f, "
            "validity=%.1f, uniqueness=%.1f, timeliness=%.1f",
            composite,
            report.grade,
            completeness,
            validity,
            uniqueness,
            timeliness,
        )
        return report

    # ------------------------------------------------------------------
    # Dimension scorers
    # ------------------------------------------------------------------

    @staticmethod
    def _completeness_score(records: List[Dict]) -> float:
        scores = [r.get("_completeness_score", 0.0) for r in records]
        return sum(scores) / len(scores) if scores else 0.0

    @staticmethod
    def _validity_score(records: List[Dict]) -> float:
        """% of records with no schema errors and no rule violations."""
        valid_count = sum(
            1
            for r in records
            if not r.get("_schema_errors") and not r.get("_rule_violations")
        )
        return valid_count / len(records) * 100 if records else 0.0

    @staticmethod
    def _uniqueness_score(
        records: List[Dict],
        duplicates_removed: int,
        original_count: Optional[int],
    ) -> float:
        total = (original_count or len(records)) + duplicates_removed
        if total == 0:
            return 100.0
        unique = len(records)
        return min(unique / total * 100, 100.0)

    def _timeliness_score(self, records: List[Dict]) -> float:
        """% of records with a list_date within max_age_days."""
        cutoff = date.today() - timedelta(days=self.max_age_days)
        with_date = [r for r in records if r.get("list_date") is not None]
        if not with_date:
            return 50.0  # Unknown timeliness – neutral score
        fresh = sum(1 for r in with_date if r["list_date"] >= cutoff)
        return fresh / len(with_date) * 100

    # ------------------------------------------------------------------
    # Issue identification
    # ------------------------------------------------------------------

    @staticmethod
    def _identify_issues(
        completeness: float,
        validity: float,
        uniqueness: float,
        timeliness: float,
    ) -> List[str]:
        issues: List[str] = []
        if completeness < 70:
            issues.append(f"Low completeness: {completeness:.1f}% (threshold 70%)")
        if validity < 80:
            issues.append(f"Low validity: {validity:.1f}% (threshold 80%)")
        if uniqueness < 95:
            issues.append(f"Elevated duplicate rate: uniqueness {uniqueness:.1f}% (threshold 95%)")
        if timeliness < 60:
            issues.append(f"Stale data: timeliness {timeliness:.1f}% (threshold 60%)")
        return issues
