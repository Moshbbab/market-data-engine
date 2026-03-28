"""
Tests for the Missing Data Handler.
"""

import pytest
from src.cleaning.missing_handler import MissingDataHandler


class TestMissingDataHandler:
    @pytest.fixture
    def handler(self):
        return MissingDataHandler()

    def _record(self, **kwargs):
        base = {
            "address": "1 Main Street",
            "price": 500000.0,
            "sqft": 1800.0,
            "bedrooms": 3,
            "bathrooms": 2.0,
            "year_built": 2005,
            "property_type": "single_family",
            "status": "active",
        }
        base.update(kwargs)
        return base

    def test_complete_records_pass_through(self, handler):
        records = [self._record()]
        result, stats = handler.handle(records)
        assert len(result) == 1
        assert stats == {}

    def test_missing_address_drops_record(self, handler):
        records = [self._record(address=None)]
        result, stats = handler.handle(records)
        assert len(result) == 0

    def test_missing_sqft_imputed_with_median(self, handler):
        records = [
            self._record(sqft=1000.0),
            self._record(sqft=2000.0),
            self._record(sqft=None),
        ]
        result, stats = handler.handle(records)
        assert len(result) == 3
        imputed = next(r for r in result if r.get("sqft") not in (1000.0, 2000.0))
        assert imputed["sqft"] == 1500.0  # median of [1000, 2000]
        assert stats.get("sqft", 0) == 1

    def test_missing_price_flagged(self, handler):
        records = [self._record(price=None)]
        result, stats = handler.handle(records)
        assert len(result) == 1
        assert "price" in result[0].get("_missing_fields", [])

    def test_custom_drop_strategy(self):
        handler = MissingDataHandler(strategies={"price": "drop"})
        records = [self._record(price=None)]
        result, _ = handler.handle(records)
        assert len(result) == 0

    def test_zero_strategy(self):
        handler = MissingDataHandler(strategies={"bedrooms": "zero"})
        records = [self._record(bedrooms=None)]
        result, stats = handler.handle(records)
        assert result[0]["bedrooms"] == 0
        assert stats.get("bedrooms") == 1

    def test_empty_input(self, handler):
        result, stats = handler.handle([])
        assert result == []
        assert stats == {}
