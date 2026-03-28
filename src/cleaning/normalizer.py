"""
Data Normalizer
===============

Standardises raw property records extracted from heterogeneous sources
into a uniform schema with consistent types, field names, and formats.

Author: Hemmah Valuation Systems
License: MIT
"""

from __future__ import annotations

import re
import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical field mapping
# Different sources use different names for the same concept.
# Map each known variant → canonical name.
# ---------------------------------------------------------------------------
_FIELD_ALIASES: Dict[str, str] = {
    # Price / value
    "list_price": "price",
    "listing_price": "price",
    "sale_price": "price",
    "assessed_value": "assessed_value",
    "zestimate": "estimated_value",
    # Area
    "sq_ft": "sqft",
    "square_feet": "sqft",
    "square_footage": "sqft",
    "living_area": "sqft",
    "gla": "sqft",
    # Lot
    "lot_sq_ft": "lot_size",
    "lot_sqft": "lot_size",
    "lot_area": "lot_size",
    # Bedrooms
    "beds": "bedrooms",
    "bed": "bedrooms",
    "br": "bedrooms",
    # Bathrooms
    "baths": "bathrooms",
    "bath": "bathrooms",
    "ba": "bathrooms",
    "full_baths": "bathrooms",
    # Year
    "year_built": "year_built",
    "yr_built": "year_built",
    "built_year": "year_built",
    # Dates
    "list_date": "list_date",
    "listing_date": "list_date",
    "sale_date": "sale_date",
    "close_date": "sale_date",
    "closed_date": "sale_date",
    # IDs
    "mls_id": "mls_id",
    "mls_number": "mls_id",
    "parcel_id": "parcel_id",
    "apn": "parcel_id",
    "zpid": "external_id",
    # Property type
    "property_type": "property_type",
    "prop_type": "property_type",
    "type": "property_type",
    # Status
    "status": "status",
    "listing_status": "status",
}

# Canonical property-type values
_PROPERTY_TYPE_MAP: Dict[str, str] = {
    "sfr": "single_family",
    "single family": "single_family",
    "single_family_residential": "single_family",
    "single family residential": "single_family",
    "residential": "single_family",
    "condo": "condo",
    "condominium": "condo",
    "townhouse": "townhouse",
    "townhome": "townhouse",
    "multi": "multi_family",
    "multi family": "multi_family",
    "multi_family": "multi_family",
    "duplex": "multi_family",
    "triplex": "multi_family",
    "quadplex": "multi_family",
    "land": "land",
    "lot": "land",
    "commercial": "commercial",
    "industrial": "industrial",
}

# Canonical status values
_STATUS_MAP: Dict[str, str] = {
    "active": "active",
    "for sale": "active",
    "available": "active",
    "pending": "pending",
    "under contract": "pending",
    "contingent": "pending",
    "sold": "sold",
    "closed": "sold",
    "expired": "expired",
    "withdrawn": "withdrawn",
    "cancelled": "cancelled",
    "canceled": "cancelled",
}


class DataNormalizer:
    """
    Transforms raw property records into a uniform canonical schema.

    Steps applied (in order):
    1. Rename aliased fields to canonical names.
    2. Normalise string values (strip whitespace, lowercase where appropriate).
    3. Cast numeric fields to their target types.
    4. Parse date strings into ``datetime.date`` objects.
    5. Normalise property_type and status to controlled vocabularies.
    6. Format address components consistently.
    7. Attach a ``normalised_at`` timestamp.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def normalize(self, records: List[Dict]) -> List[Dict]:
        """
        Normalise a list of raw property records.

        Args:
            records: Raw records from any extraction source.

        Returns:
            List of normalised property records.
        """
        normalised: List[Dict] = []
        for record in records:
            try:
                normalised.append(self._normalize_record(record))
            except Exception as exc:  # pragma: no cover – log and continue
                self.logger.warning("Failed to normalise record %s: %s", record.get("mls_id", "?"), exc)
        self.logger.info("Normalised %d / %d records", len(normalised), len(records))
        return normalised

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _normalize_record(self, record: Dict) -> Dict:
        result: Dict = {}

        # 1. Rename aliased fields
        for raw_key, value in record.items():
            canonical = _FIELD_ALIASES.get(raw_key.lower().strip(), raw_key.lower().strip())
            result[canonical] = value

        # 2. String normalisation
        for key, value in result.items():
            if isinstance(value, str):
                result[key] = value.strip()

        # 3. Numeric fields
        result["price"] = self._to_float(result.get("price"))
        result["assessed_value"] = self._to_float(result.get("assessed_value"))
        result["estimated_value"] = self._to_float(result.get("estimated_value"))
        result["sqft"] = self._to_float(result.get("sqft"))
        result["lot_size"] = self._to_float(result.get("lot_size"))
        result["bedrooms"] = self._to_int(result.get("bedrooms"))
        result["bathrooms"] = self._to_float(result.get("bathrooms"))
        result["year_built"] = self._to_int(result.get("year_built"))

        # 4. Date fields
        result["list_date"] = self._to_date(result.get("list_date"))
        result["sale_date"] = self._to_date(result.get("sale_date"))

        # 5. Controlled vocabularies
        raw_type = str(result.get("property_type", "")).lower().strip()
        result["property_type"] = _PROPERTY_TYPE_MAP.get(raw_type, raw_type or None)

        raw_status = str(result.get("status", "")).lower().strip()
        result["status"] = _STATUS_MAP.get(raw_status, raw_status or None)

        # 6. Address normalisation
        if "address" in result and isinstance(result["address"], str):
            result["address"] = self._normalize_address(result["address"])

        # 7. Metadata
        result["normalised_at"] = datetime.now(timezone.utc).isoformat()

        # Remove None-keyed or empty artefacts
        result = {k: v for k, v in result.items() if k}

        return result

    # ------------------------------------------------------------------
    # Type coercion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, float):
            return value
        if isinstance(value, int):
            return float(value)
        if isinstance(value, str):
            # Remove currency symbols and commas
            cleaned = re.sub(r"[,$\s]", "", value)
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    @staticmethod
    def _to_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            cleaned = re.sub(r"[^0-9]", "", value)
            return int(cleaned) if cleaned else None
        return None

    @staticmethod
    def _to_date(value: Any) -> Optional[date]:
        if value is None:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y", "%Y%m%d"):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
        return None

    @staticmethod
    def _normalize_address(address: str) -> str:
        """Apply lightweight address standardisation."""
        abbrevs = {
            r"\bSt\b\.?": "Street",
            r"\bAve\b\.?": "Avenue",
            r"\bBlvd\b\.?": "Boulevard",
            r"\bDr\b\.?": "Drive",
            r"\bLn\b\.?": "Lane",
            r"\bRd\b\.?": "Road",
            r"\bCt\b\.?": "Court",
            r"\bPl\b\.?": "Place",
            r"\bN\b\.?": "North",
            r"\bS\b\.?": "South",
            r"\bE\b\.?": "East",
            r"\bW\b\.?": "West",
        }
        result = " ".join(address.split())  # Collapse whitespace
        result = result.title()
        for pattern, replacement in abbrevs.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result
