"""
Market Data Pipeline
====================

Unified end-to-end pipeline that chains:
  Extraction → Cleaning → Validation

and exposes a single ``run()`` entry point for the full workflow.

Author: Hemmah Valuation Systems
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

from .extraction.data_extractor import DataExtractor, DataSource, ExtractionResult
from .cleaning.cleaner import DataCleaner, CleaningResult
from .validation.validator import DataValidator, ValidationResult

@dataclass
class PipelineResult:
    """Aggregated result of a full pipeline run."""

    location: str
    property_type: str
    extraction_results: Dict[str, ExtractionResult]
    cleaning_result: CleaningResult
    validation_result: ValidationResult
    run_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_records(self) -> int:
        """Number of records that passed the full pipeline."""
        return self.validation_result.valid_count

    @property
    def quality_score(self) -> float:
        return self.validation_result.quality_score

    @property
    def freshness_hours(self) -> float:
        """Hours since the pipeline run."""
        delta = datetime.now(timezone.utc) - self.run_at
        return round(delta.total_seconds() / 3600, 2)


class MarketDataPipeline:
    """
    End-to-end market data pipeline.

    Orchestrates extraction from multiple sources, cleans the raw data,
    and validates quality – returning a single :class:`PipelineResult`.

    Args:
        sources:           List of source name strings or :class:`DataSource` objects.
        quality_threshold: Minimum acceptable quality score (0-100). Default 70.
        enable_monitoring: Log quality metrics after each run. Default True.
        merge_duplicates:  Merge (rather than drop) duplicate records. Default True.
        outlier_method:    ``"iqr"``, ``"zscore"``, or ``"both"``. Default ``"iqr"``.
        missing_strategies: Field-level missing-data strategies for the cleaner.
        max_age_days:      Timeliness window in days for quality scoring. Default 30.
    """

    def __init__(
        self,
        sources: Optional[List[Union[str, DataSource]]] = None,
        quality_threshold: float = 70.0,
        enable_monitoring: bool = True,
        merge_duplicates: bool = True,
        outlier_method: str = "iqr",
        missing_strategies: Optional[Dict[str, str]] = None,
        max_age_days: int = 30,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.quality_threshold = quality_threshold
        self.enable_monitoring = enable_monitoring

        self._extractor = DataExtractor(sources=sources)
        self._cleaner = DataCleaner(
            merge_duplicates=merge_duplicates,
            outlier_method=outlier_method,
            missing_strategies=missing_strategies,
        )
        self._validator = DataValidator(
            quality_threshold=quality_threshold,
            max_age_days=max_age_days,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        location: str,
        property_type: str = "residential",
        date_range: Optional[tuple] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        **kwargs,
    ) -> PipelineResult:
        """
        Execute the full pipeline for the given search parameters.

        Args:
            location:      Geographic location (city, ZIP, etc.)
            property_type: Property type filter.
            date_range:    Optional (start_date, end_date) tuple.
            min_price:     Optional minimum price filter.
            max_price:     Optional maximum price filter.
            **kwargs:      Additional source-specific parameters.

        Returns:
            :class:`PipelineResult` with all intermediate and final results.
        """
        self.logger.info(
            "Pipeline starting: location=%s, type=%s", location, property_type
        )

        # --- Stage 1: Extraction ---
        extraction_results = self._extractor.extract(
            location=location,
            property_type=property_type,
            date_range=date_range,
            min_price=min_price,
            max_price=max_price,
            **kwargs,
        )

        # Aggregate all raw records across sources
        raw_records: List[Dict] = []
        for source_name, result in extraction_results.items():
            if result.success:
                raw_records.extend(result.records)
                self.logger.info("Source '%s': %d records", source_name, result.total_count)
            else:
                self.logger.warning(
                    "Source '%s' failed: %s", source_name, result.errors
                )

        self.logger.info("Total raw records extracted: %d", len(raw_records))

        # --- Stage 2: Cleaning ---
        cleaning_result = self._cleaner.clean(raw_records)

        # --- Stage 3: Validation ---
        validation_result = self._validator.validate(
            cleaning_result.records,
            duplicates_removed=cleaning_result.duplicates_removed,
            original_count=len(raw_records),
        )

        # --- Monitoring ---
        if self.enable_monitoring:
            self._log_metrics(cleaning_result, validation_result)

        pipeline_result = PipelineResult(
            location=location,
            property_type=property_type,
            extraction_results=extraction_results,
            cleaning_result=cleaning_result,
            validation_result=validation_result,
        )

        self.logger.info(
            "Pipeline complete: %d valid records, quality=%.1f/100 (grade %s)",
            pipeline_result.total_records,
            pipeline_result.quality_score,
            validation_result.quality_report.grade,
        )
        return pipeline_result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log_metrics(
        self,
        cleaning: CleaningResult,
        validation: ValidationResult,
    ) -> None:
        qr = validation.quality_report
        self.logger.info(
            "[METRICS] quality=%.1f | completeness=%.1f | validity=%.1f | "
            "uniqueness=%.1f | timeliness=%.1f | dupes_removed=%d | outliers=%d",
            qr.composite_score,
            qr.completeness_score,
            qr.validity_score,
            qr.uniqueness_score,
            qr.timeliness_score,
            cleaning.duplicates_removed,
            cleaning.outliers_flagged,
        )
        if qr.issues:
            for issue in qr.issues:
                self.logger.warning("[QUALITY ISSUE] %s", issue)
