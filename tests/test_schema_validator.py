"""
Tests for the Schema Validator.
"""

import pytest
from datetime import date
from src.validation.schema_validator import SchemaValidator


class TestSchemaValidator:
    @pytest.fixture
    def validator(self):
        return SchemaValidator()

    def _valid_record(self):
        return {
            "address": "1 Main Street",
            "price": 500000.0,
            "sqft": 1800.0,
            "bedrooms": 3,
            "bathrooms": 2.0,
            "year_built": 2005,
            "property_type": "single_family",
            "status": "active",
            "list_date": date(2024, 1, 15),
            "source": "mls",
        }

    def test_valid_record_passes(self, validator):
        valid, invalid = validator.validate([self._valid_record()])
        assert len(valid) == 1
        assert len(invalid) == 0

    def test_missing_required_address_fails(self, validator):
        record = self._valid_record()
        del record["address"]
        valid, invalid = validator.validate([record])
        assert len(invalid) == 1
        assert any(e["field"] == "address" for e in invalid[0]["_schema_errors"])

    def test_wrong_type_price_fails(self, validator):
        record = self._valid_record()
        record["price"] = "not-a-number"
        valid, invalid = validator.validate([record])
        assert len(invalid) == 1

    def test_int_accepted_for_float_field(self, validator):
        record = self._valid_record()
        record["price"] = 500000  # int, not float – should still pass
        valid, invalid = validator.validate([record])
        assert len(valid) == 1

    def test_none_optional_field_passes(self, validator):
        record = self._valid_record()
        record["lot_size"] = None
        valid, invalid = validator.validate([record])
        assert len(valid) == 1

    def test_multiple_records_mixed(self, validator):
        good = self._valid_record()
        bad = self._valid_record()
        del bad["address"]
        valid, invalid = validator.validate([good, bad])
        assert len(valid) == 1
        assert len(invalid) == 1

    def test_validate_record_returns_errors_list(self, validator):
        record = self._valid_record()
        del record["address"]
        errors = validator.validate_record(record)
        assert len(errors) >= 1
