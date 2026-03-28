"""
Data Cleaner
============

Unified façade that orchestrates the full cleaning pipeline:
  1. Normalise raw records (field names, types, formats)
  2. Deduplicate (remove/merge duplicate records)
  3. Detect outliers (flag anomalous values)
  4. Handle missing data (impute or drop)

Author: Hemmah Valuation Systems
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .normalizer import DataNormalizer
from .deduplicator import Deduplicator
from .outlier_detector import OutlierDetector
from .missing_handler import MissingDataHandler


@dataclass
class CleaningResult:
    """Summary of a cleaning run."""

    input_count: int
    output_count: int
    duplicates_removed: int
    outliers_flagged: int
    records: List[Dict]
    imputation_stats: Dict[str, int]
    cleaned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def retention_rate(self) -> float:
        """Fraction of input records retained after cleaning."""
        if self.input_count == 0:
            return 0.0
        return self.output_count / self.input_count


class DataCleaner:
    """
    Run the full data-cleaning pipeline on a list of raw records.

    Args:
        merge_duplicates: Merge duplicate records (default True).
        outlier_method:   Outlier detection method – ``"iqr"``, ``"zscore"``,
                          or ``"both"`` (default ``"iqr"``).
        missing_strategies: Field-level missing-data strategies passed to
                            :class:`MissingDataHandler`.
    """

    def __init__(
        self,
        merge_duplicates: bool = True,
        outlier_method: str = "iqr",
        missing_strategies: Optional[Dict[str, str]] = None,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self._normalizer = DataNormalizer()
        self._deduplicator = Deduplicator(merge=merge_duplicates)
        self._outlier_detector = OutlierDetector(method=outlier_method)
        self._missing_handler = MissingDataHandler(strategies=missing_strategies)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def clean(self, records: List[Dict]) -> CleaningResult:
        """
        Execute the full cleaning pipeline.

        Args:
            records: Raw records from the extraction layer.

        Returns:
            :class:`CleaningResult` with cleaned records and statistics.
        """
        self.logger.info("Starting cleaning pipeline on %d records", len(records))
        input_count = len(records)

        # Step 1 – Normalise
        normalised = self._normalizer.normalize(records)

        # Step 2 – Deduplicate
        deduped, duplicates_removed = self._deduplicator.deduplicate(normalised)

        # Step 3 – Detect outliers
        outlier_flagged = self._outlier_detector.detect(deduped)
        outliers_count = sum(1 for r in outlier_flagged if r.get("_is_outlier"))

        # Step 4 – Handle missing data
        final_records, imputation_stats = self._missing_handler.handle(outlier_flagged)

        result = CleaningResult(
            input_count=input_count,
            output_count=len(final_records),
            duplicates_removed=duplicates_removed,
            outliers_flagged=outliers_count,
            records=final_records,
            imputation_stats=imputation_stats,
        )

        self.logger.info(
            "Cleaning complete: %d → %d records (dupes removed: %d, outliers flagged: %d)",
            input_count,
            len(final_records),
            duplicates_removed,
            outliers_count,
        )
        return result
