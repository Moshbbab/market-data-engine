"""
Tests for the Business Rules Validator.
"""

import pytest
from datetime import date
from src.validation.business_rules import BusinessRulesValidator


class TestBusinessRulesValidator:
    @pytest.fixture
    def validator(self):
        return BusinessRulesValidator()

    def _valid(self, **overrides):
        rec = {
            "address": "1 Main Street",
            "price": 500000.0,
            "sqft": 1800.0,
            "bedrooms": 3,
            "bathrooms": 2.0,
            "year_built": 2005,
            "lot_size": 5000.0,
            "property_type": "single_family",
            "status": "active",
        }
        rec.update(overrides)
        return rec

    def test_valid_record_passes(self, validator):
        passed, failed = validator.validate([self._valid()])
        assert len(passed) == 1
        assert len(failed) == 0

    def test_negative_price_fails(self, validator):
        passed, failed = validator.validate([self._valid(price=-1.0)])
        assert len(failed) == 1

    def test_zero_price_fails(self, validator):
        passed, failed = validator.validate([self._valid(price=0.0)])
        assert len(failed) == 1

    def test_negative_sqft_fails(self, validator):
        passed, failed = validator.validate([self._valid(sqft=-100.0)])
        assert len(failed) == 1

    def test_negative_bedrooms_fails(self, validator):
        passed, failed = validator.validate([self._valid(bedrooms=-1)])
        assert len(failed) == 1

    def test_year_built_too_old_fails(self, validator):
        passed, failed = validator.validate([self._valid(year_built=1700)])
        assert len(failed) == 1

    def test_year_built_future_fails(self, validator):
        future_year = date.today().year + 5
        passed, failed = validator.validate([self._valid(year_built=future_year)])
        assert len(failed) == 1

    def test_invalid_property_type_is_warning_not_error(self, validator):
        passed, failed = validator.validate([self._valid(property_type="mansion")])
        # Should pass (warning only) but carry a warning key
        assert len(passed) == 1
        assert "mansion" in str(passed[0].get("_rule_warnings", ""))

    def test_none_optional_fields_pass(self, validator):
        rec = self._valid()
        rec["sqft"] = None
        rec["lot_size"] = None
        passed, failed = validator.validate([rec])
        assert len(passed) == 1

    def test_check_record_returns_list(self, validator):
        violations = validator.check_record(self._valid(price=-1.0))
        assert len(violations) >= 1

    def test_empty_list(self, validator):
        passed, failed = validator.validate([])
        assert passed == []
        assert failed == []
