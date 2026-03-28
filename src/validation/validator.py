"""
Data Validator
==============

Unified façade that orchestrates the full validation pipeline:
  1. Schema validation   – required fields, correct types
  2. Business rules      – domain logic (price > 0, valid year_built, etc.)
  3. Completeness check  – key-field presence scoring
  4. Quality scoring     – composite 0-100 score across all dimensions

Author: Hemmah Valuation Systems
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .schema_validator import SchemaValidator
from .business_rules import BusinessRulesValidator
from .completeness_checker import CompletenessChecker
from .quality_scorer import QualityScorer, QualityReport


@dataclass
class ValidationResult:
    """Summary of a full validation run."""

    input_count: int
    valid_count: int
    invalid_count: int
    quality_report: QualityReport
    valid_records: List[Dict]
    invalid_records: List[Dict]
    completeness_summary: Dict
    validated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def quality_score(self) -> float:
        return self.quality_report.composite_score

    @property
    def issues(self) -> List[str]:
        return self.quality_report.issues


class DataValidator:
    """
    Run the full validation pipeline on cleaned property records.

    Args:
        quality_threshold: Minimum acceptable composite quality score (0-100).
        max_age_days:      Timeliness window for quality scoring.
    """

    def __init__(
        self,
        quality_threshold: float = 70.0,
        max_age_days: int = 30,
    ) -> None:
        self.quality_threshold = quality_threshold
        self.logger = logging.getLogger(__name__)
        self._schema_validator = SchemaValidator()
        self._rules_validator = BusinessRulesValidator()
        self._completeness_checker = CompletenessChecker(threshold=quality_threshold)
        self._quality_scorer = QualityScorer(max_age_days=max_age_days)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(
        self,
        records: List[Dict],
        duplicates_removed: int = 0,
        original_count: Optional[int] = None,
    ) -> ValidationResult:
        """
        Execute the full validation pipeline.

        Args:
            records:           Cleaned property records from DataCleaner.
            duplicates_removed: Count of duplicates removed (for uniqueness scoring).
            original_count:    Original record count before cleaning.

        Returns:
            :class:`ValidationResult` with full quality report and record lists.
        """
        self.logger.info("Starting validation pipeline on %d records", len(records))
        input_count = len(records)

        # Step 1 – Schema validation
        schema_valid, schema_invalid = self._schema_validator.validate(records)

        # Step 2 – Business rules (applied only to schema-valid records)
        rules_passed, rules_failed = self._rules_validator.validate(schema_valid)

        # Combine invalid records
        all_invalid = schema_invalid + rules_failed

        # Step 3 – Completeness check (on all records for full picture)
        all_records = rules_passed + all_invalid
        annotated, completeness_summary = self._completeness_checker.check(all_records)

        # Re-separate after annotation
        valid_annotated = [r for r in annotated if r not in all_invalid]
        invalid_annotated = [r for r in annotated if r in all_invalid]

        # Step 4 – Quality scoring
        quality_report = self._quality_scorer.score(
            valid_annotated,
            duplicates_removed=duplicates_removed,
            original_count=original_count,
        )

        result = ValidationResult(
            input_count=input_count,
            valid_count=len(valid_annotated),
            invalid_count=len(invalid_annotated),
            quality_report=quality_report,
            valid_records=valid_annotated,
            invalid_records=invalid_annotated,
            completeness_summary=completeness_summary,
        )

        self.logger.info(
            "Validation complete: %d valid, %d invalid, quality score=%.1f/100 (grade %s)",
            result.valid_count,
            result.invalid_count,
            result.quality_score,
            quality_report.grade,
        )
        return result
