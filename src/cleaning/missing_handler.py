"""
Missing Data Handler
====================

Handles missing values in property records using configurable imputation
and flagging strategies.

Strategies per field:
- ``"median"``  – Replace with the median of non-null values in the batch.
- ``"mean"``    – Replace with the mean.
- ``"mode"``    – Replace with the most frequent value.
- ``"flag"``    – Leave as None but mark the record with a missing flag.
- ``"drop"``    – Records missing this field are removed from the output.
- ``"zero"``    – Replace with 0 (useful for counts like bathrooms).

Author: Hemmah Valuation Systems
License: MIT
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Default field strategies for real-estate data
_DEFAULT_STRATEGIES: Dict[str, str] = {
    "price": "flag",
    "sqft": "median",
    "lot_size": "median",
    "bedrooms": "median",
    "bathrooms": "median",
    "year_built": "median",
    "property_type": "flag",
    "status": "flag",
    "address": "drop",
}


class MissingDataHandler:
    """
    Impute or flag missing values in property records.

    Args:
        strategies: Mapping of field → strategy. Merged with built-in defaults.
        required_fields: Fields whose absence causes a record to be dropped,
            regardless of the strategy setting.
    """

    def __init__(
        self,
        strategies: Optional[Dict[str, str]] = None,
        required_fields: Optional[List[str]] = None,
    ) -> None:
        self.strategies: Dict[str, str] = {**_DEFAULT_STRATEGIES, **(strategies or {})}
        self.required_fields: Set[str] = set(required_fields or ["address"])
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle(self, records: List[Dict]) -> Tuple[List[Dict], Dict[str, int]]:
        """
        Apply missing-data strategies to *records*.

        Args:
            records: Normalised (and optionally outlier-flagged) records.

        Returns:
            Tuple of (processed records, dict of imputation counts per field).
        """
        stats: Dict[str, int] = {}

        # Compute batch statistics for imputation strategies
        batch_stats = self._compute_batch_stats(records)

        kept: List[Dict] = []
        for record in records:
            result, dropped = self._handle_record(record, batch_stats, stats)
            if not dropped:
                kept.append(result)

        self.logger.info(
            "Missing data handling complete: %d records kept (of %d), imputation stats: %s",
            len(kept),
            len(records),
            stats,
        )
        return kept, stats

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_batch_stats(self, records: List[Dict]) -> Dict[str, Dict[str, Any]]:
        """Pre-compute median / mean / mode for all configured fields."""
        stats: Dict[str, Dict[str, Any]] = {}

        for field, strategy in self.strategies.items():
            if strategy not in ("median", "mean", "mode"):
                continue

            values = [r[field] for r in records if r.get(field) is not None]
            if not values:
                stats[field] = {}
                continue

            if strategy == "mode":
                most_common = Counter(values).most_common(1)
                stats[field] = {"mode": most_common[0][0] if most_common else None}
            else:
                numeric = [float(v) for v in values if isinstance(v, (int, float))]
                if not numeric:
                    stats[field] = {}
                    continue
                numeric.sort()
                n = len(numeric)
                median = (
                    numeric[n // 2]
                    if n % 2 == 1
                    else (numeric[n // 2 - 1] + numeric[n // 2]) / 2
                )
                mean = sum(numeric) / n
                stats[field] = {"median": median, "mean": mean}

        return stats

    def _handle_record(
        self,
        record: Dict,
        batch_stats: Dict[str, Dict[str, Any]],
        stats: Dict[str, int],
    ) -> Tuple[Dict, bool]:
        """
        Apply strategies to a single record.

        Returns (processed_record, was_dropped).
        """
        result = dict(record)
        missing_flags: List[str] = []

        # Drop records missing required fields immediately
        for req in self.required_fields:
            if result.get(req) is None:
                self.logger.debug("Dropping record missing required field '%s'", req)
                return result, True

        for field, strategy in self.strategies.items():
            if result.get(field) is not None:
                continue  # Not missing

            if strategy == "drop":
                return result, True

            elif strategy == "flag":
                missing_flags.append(field)

            elif strategy == "zero":
                result[field] = 0
                stats[field] = stats.get(field, 0) + 1

            elif strategy in ("median", "mean", "mode"):
                field_stats = batch_stats.get(field, {})
                imputed = field_stats.get(strategy)
                if imputed is not None:
                    result[field] = imputed
                    stats[field] = stats.get(field, 0) + 1
                else:
                    # Fallback to flag when no batch stat available
                    missing_flags.append(field)

        if missing_flags:
            existing: List[str] = result.get("_missing_fields", [])
            result["_missing_fields"] = existing + missing_flags

        return result, False
