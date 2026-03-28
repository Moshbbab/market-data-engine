"""
Schema Validator
================

Validates that property records conform to the expected field schema
(required fields present, correct data types).

Author: Hemmah Valuation Systems
License: MIT
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple, Type

logger = logging.getLogger(__name__)

# Schema definition: field_name → (python_type, required)
PROPERTY_SCHEMA: Dict[str, Tuple[Type, bool]] = {
    "address":       (str,   True),
    "price":         (float, False),
    "sqft":          (float, False),
    "bedrooms":      (int,   False),
    "bathrooms":     (float, False),
    "year_built":    (int,   False),
    "property_type": (str,   False),
    "status":        (str,   False),
    "lot_size":      (float, False),
    "list_date":     (date,  False),
    "source":        (str,   False),
}


class SchemaValidationError:
    """Represents a single schema violation."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message

    def __repr__(self) -> str:
        return f"SchemaValidationError(field={self.field!r}, message={self.message!r})"


class SchemaValidator:
    """
    Validate records against the canonical property schema.

    Args:
        schema: Custom schema overriding the default. Maps field name to
                ``(type, required)`` tuples.
    """

    def __init__(self, schema: Optional[Dict[str, Tuple[Type, bool]]] = None) -> None:
        self.schema = schema or PROPERTY_SCHEMA
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, records: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Validate all records.

        Args:
            records: Cleaned property records.

        Returns:
            Tuple of (valid_records, invalid_records). Invalid records have a
            ``_schema_errors`` key listing their violations.
        """
        valid: List[Dict] = []
        invalid: List[Dict] = []

        for record in records:
            errors = self._validate_record(record)
            if errors:
                record = dict(record)
                record["_schema_errors"] = [
                    {"field": e.field, "message": e.message} for e in errors
                ]
                invalid.append(record)
            else:
                valid.append(record)

        self.logger.info(
            "Schema validation: %d valid, %d invalid", len(valid), len(invalid)
        )
        return valid, invalid

    def validate_record(self, record: Dict) -> List[SchemaValidationError]:
        """Validate a single record. Convenience wrapper."""
        return self._validate_record(record)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_record(self, record: Dict) -> List[SchemaValidationError]:
        errors: List[SchemaValidationError] = []

        for field_name, (expected_type, required) in self.schema.items():
            value = record.get(field_name)

            if value is None:
                if required:
                    errors.append(
                        SchemaValidationError(
                            field_name, f"Required field '{field_name}' is missing."
                        )
                    )
                continue  # Optional fields may be None

            if not isinstance(value, expected_type):
                # Allow int where float is expected (int is a subtype of float conceptually)
                if expected_type is float and isinstance(value, int):
                    continue
                errors.append(
                    SchemaValidationError(
                        field_name,
                        f"Expected {expected_type.__name__}, got {type(value).__name__}.",
                    )
                )

        return errors
