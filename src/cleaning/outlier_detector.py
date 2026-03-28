"""
Outlier Detector
================

Identifies statistical outliers in numeric property fields using
the Interquartile Range (IQR) and Z-score methods.

Fields inspected by default:
- price
- sqft
- price_per_sqft (derived)
- lot_size
- bedrooms
- bathrooms

Author: Hemmah Valuation Systems
License: MIT
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Default fields to inspect for outliers
_DEFAULT_FIELDS: List[str] = ["price", "sqft", "lot_size", "bedrooms", "bathrooms"]

# IQR multiplier (Tukey's fence)
_IQR_MULTIPLIER = 1.5

# Z-score threshold
_Z_SCORE_THRESHOLD = 3.0


def _mean(values: List[float]) -> float:
    return sum(values) / len(values)


def _std(values: List[float], mu: float) -> float:
    variance = sum((v - mu) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def _quartiles(sorted_values: List[float]) -> Tuple[float, float]:
    """Return (Q1, Q3) for a pre-sorted list."""
    n = len(sorted_values)
    q1 = sorted_values[n // 4]
    q3 = sorted_values[(3 * n) // 4]
    return q1, q3


class OutlierDetector:
    """
    Detect outlier records based on numeric field distributions.

    Two detection methods are supported and can be combined:
    - ``"iqr"``     – Tukey's IQR fence (default).
    - ``"zscore"``  – Z-score threshold.

    Outliers are *flagged* (a ``_outlier_fields`` key is added) rather
    than silently removed, giving downstream validation full visibility.

    Args:
        fields:     Numeric fields to inspect. Defaults to standard RE fields.
        method:     ``"iqr"``, ``"zscore"``, or ``"both"``.
        iqr_mult:   IQR fence multiplier (default 1.5).
        z_thresh:   Z-score threshold (default 3.0).
    """

    def __init__(
        self,
        fields: Optional[List[str]] = None,
        method: str = "iqr",
        iqr_mult: float = _IQR_MULTIPLIER,
        z_thresh: float = _Z_SCORE_THRESHOLD,
    ) -> None:
        self.fields = fields or _DEFAULT_FIELDS
        self.method = method
        self.iqr_mult = iqr_mult
        self.z_thresh = z_thresh
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, records: List[Dict]) -> List[Dict]:
        """
        Flag outlier records.

        Each record that has at least one outlier field gets an
        ``_outlier_fields`` key containing the set of offending fields,
        and an ``_is_outlier`` flag set to True.

        Args:
            records: Normalised property records.

        Returns:
            The same list with outlier flags added in-place.
        """
        if len(records) < 4:
            self.logger.warning("Too few records (%d) for outlier detection; skipping.", len(records))
            return records

        for field in self.fields:
            self._detect_field(records, field)

        # Derive price_per_sqft and check it separately
        self._add_price_per_sqft(records)
        if len([r for r in records if r.get("price_per_sqft") is not None]) >= 4:
            self._detect_field(records, "price_per_sqft")

        outlier_count = sum(1 for r in records if r.get("_is_outlier"))
        self.logger.info(
            "Outlier detection complete: %d / %d records flagged",
            outlier_count,
            len(records),
        )
        return records

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_field(self, records: List[Dict], field: str) -> None:
        values_with_idx: List[Tuple[int, float]] = [
            (i, float(r[field]))
            for i, r in enumerate(records)
            if r.get(field) is not None and isinstance(r[field], (int, float))
        ]

        if len(values_with_idx) < 4:
            return

        values = [v for _, v in values_with_idx]
        sorted_vals = sorted(values)

        use_iqr = self.method in ("iqr", "both")
        use_z = self.method in ("zscore", "both")

        lower_iqr = upper_iqr = lower_z = upper_z = None

        if use_iqr:
            q1, q3 = _quartiles(sorted_vals)
            iqr = q3 - q1
            lower_iqr = q1 - self.iqr_mult * iqr
            upper_iqr = q3 + self.iqr_mult * iqr

        if use_z:
            mu = _mean(values)
            sigma = _std(values, mu)
            if sigma > 0:
                lower_z = mu - self.z_thresh * sigma
                upper_z = mu + self.z_thresh * sigma

        for idx, value in values_with_idx:
            is_outlier = False

            if use_iqr and lower_iqr is not None and upper_iqr is not None:
                if value < lower_iqr or value > upper_iqr:
                    is_outlier = True

            if use_z and lower_z is not None and upper_z is not None:
                if value < lower_z or value > upper_z:
                    is_outlier = True

            if is_outlier:
                record = records[idx]
                record["_is_outlier"] = True
                flagged: Set[str] = record.get("_outlier_fields", set())
                flagged.add(field)
                record["_outlier_fields"] = flagged

    @staticmethod
    def _add_price_per_sqft(records: List[Dict]) -> None:
        for record in records:
            price = record.get("price")
            sqft = record.get("sqft")
            if price and sqft and sqft > 0:
                record["price_per_sqft"] = round(price / sqft, 2)
