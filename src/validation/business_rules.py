"""
Business Rules Validator
========================

Applies domain-specific real-estate business rules to property records.

Rules enforced:
- price must be > 0 when present
- sqft must be > 0 when present
- bedrooms must be >= 0 when present
- bathrooms must be >= 0 when present
- year_built must be between 1800 and current year when present
- lot_size must be >= 0 when present
- property_type must be in the controlled vocabulary
- status must be in the controlled vocabulary
- price_per_sqft (when derivable) must be reasonable (<= 50,000 $/sqft)

Author: Hemmah Valuation Systems
License: MIT
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_VALID_PROPERTY_TYPES = {
    "single_family",
    "condo",
    "townhouse",
    "multi_family",
    "land",
    "commercial",
    "industrial",
}

_VALID_STATUSES = {
    "active",
    "pending",
    "sold",
    "expired",
    "withdrawn",
    "cancelled",
}

_MIN_YEAR_BUILT = 1800
_MAX_PRICE_PER_SQFT = 50_000.0


class RuleViolation:
    """Represents a single business-rule violation."""

    def __init__(self, rule: str, message: str, severity: str = "error") -> None:
        self.rule = rule
        self.message = message
        self.severity = severity  # "error" | "warning"

    def __repr__(self) -> str:
        return f"RuleViolation(rule={self.rule!r}, severity={self.severity!r}, msg={self.message!r})"


class BusinessRulesValidator:
    """
    Validate property records against real-estate business rules.

    Args:
        max_price_per_sqft: Maximum sensible price-per-sqft (default 50 000).
    """

    def __init__(self, max_price_per_sqft: float = _MAX_PRICE_PER_SQFT) -> None:
        self.max_price_per_sqft = max_price_per_sqft
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, records: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Apply business rules to all records.

        Returns:
            Tuple of (passed_records, failed_records). Failed records carry
            a ``_rule_violations`` key.
        """
        passed: List[Dict] = []
        failed: List[Dict] = []

        for record in records:
            violations = self._check_record(record)
            errors = [v for v in violations if v.severity == "error"]
            warnings = [v for v in violations if v.severity == "warning"]

            rec = dict(record)
            if warnings:
                rec["_rule_warnings"] = [
                    {"rule": v.rule, "message": v.message} for v in warnings
                ]

            if errors:
                rec["_rule_violations"] = [
                    {"rule": v.rule, "message": v.message} for v in errors
                ]
                failed.append(rec)
            else:
                passed.append(rec)

        self.logger.info(
            "Business rule validation: %d passed, %d failed", len(passed), len(failed)
        )
        return passed, failed

    def check_record(self, record: Dict) -> List[RuleViolation]:
        """Check a single record. Convenience wrapper."""
        return self._check_record(record)

    # ------------------------------------------------------------------
    # Internal rule checks
    # ------------------------------------------------------------------

    def _check_record(self, record: Dict) -> List[RuleViolation]:
        violations: List[RuleViolation] = []
        violations += self._check_price(record)
        violations += self._check_sqft(record)
        violations += self._check_bedrooms(record)
        violations += self._check_bathrooms(record)
        violations += self._check_year_built(record)
        violations += self._check_lot_size(record)
        violations += self._check_property_type(record)
        violations += self._check_status(record)
        violations += self._check_price_per_sqft(record)
        return violations

    @staticmethod
    def _check_price(record: Dict) -> List[RuleViolation]:
        price = record.get("price")
        if price is not None and price <= 0:
            return [RuleViolation("PRICE_POSITIVE", f"Price must be > 0, got {price}.")]
        return []

    @staticmethod
    def _check_sqft(record: Dict) -> List[RuleViolation]:
        sqft = record.get("sqft")
        if sqft is not None and sqft <= 0:
            return [RuleViolation("SQFT_POSITIVE", f"sqft must be > 0, got {sqft}.")]
        return []

    @staticmethod
    def _check_bedrooms(record: Dict) -> List[RuleViolation]:
        beds = record.get("bedrooms")
        if beds is not None and beds < 0:
            return [RuleViolation("BEDROOMS_NON_NEGATIVE", f"Bedrooms must be >= 0, got {beds}.")]
        return []

    @staticmethod
    def _check_bathrooms(record: Dict) -> List[RuleViolation]:
        baths = record.get("bathrooms")
        if baths is not None and baths < 0:
            return [RuleViolation("BATHROOMS_NON_NEGATIVE", f"Bathrooms must be >= 0, got {baths}.")]
        return []

    @staticmethod
    def _check_year_built(record: Dict) -> List[RuleViolation]:
        year = record.get("year_built")
        if year is not None:
            current_year = date.today().year
            if year < _MIN_YEAR_BUILT or year > current_year:
                return [
                    RuleViolation(
                        "YEAR_BUILT_RANGE",
                        f"year_built {year} outside valid range [{_MIN_YEAR_BUILT}, {current_year}].",
                    )
                ]
        return []

    @staticmethod
    def _check_lot_size(record: Dict) -> List[RuleViolation]:
        lot = record.get("lot_size")
        if lot is not None and lot < 0:
            return [RuleViolation("LOT_SIZE_NON_NEGATIVE", f"lot_size must be >= 0, got {lot}.")]
        return []

    @staticmethod
    def _check_property_type(record: Dict) -> List[RuleViolation]:
        pt = record.get("property_type")
        if pt is not None and pt not in _VALID_PROPERTY_TYPES:
            return [
                RuleViolation(
                    "PROPERTY_TYPE_INVALID",
                    f"Unknown property_type '{pt}'. Valid: {sorted(_VALID_PROPERTY_TYPES)}.",
                    severity="warning",
                )
            ]
        return []

    @staticmethod
    def _check_status(record: Dict) -> List[RuleViolation]:
        status = record.get("status")
        if status is not None and status not in _VALID_STATUSES:
            return [
                RuleViolation(
                    "STATUS_INVALID",
                    f"Unknown status '{status}'. Valid: {sorted(_VALID_STATUSES)}.",
                    severity="warning",
                )
            ]
        return []

    def _check_price_per_sqft(self, record: Dict) -> List[RuleViolation]:
        price = record.get("price")
        sqft = record.get("sqft")
        if price and sqft and sqft > 0:
            ppsf = price / sqft
            if ppsf > self.max_price_per_sqft:
                return [
                    RuleViolation(
                        "PRICE_PER_SQFT_HIGH",
                        f"price/sqft ({ppsf:.2f}) exceeds threshold ({self.max_price_per_sqft}).",
                        severity="warning",
                    )
                ]
        return []
