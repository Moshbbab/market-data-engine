"""
Tests for the Deduplicator.
"""

import pytest
from src.cleaning.deduplicator import Deduplicator, _canonical_address


class TestCanonicalAddress:
    def test_lowercase_and_stripped(self):
        assert _canonical_address("  123 Main St  ", "LA") == "123 main st la"

    def test_punctuation_removed(self):
        assert _canonical_address("123 Main St.", "L.A.") == "123 main st la"

    def test_none_address_returns_empty(self):
        assert _canonical_address(None) == ""


class TestDeduplicator:
    @pytest.fixture
    def dedup(self):
        return Deduplicator(merge=True)

    def _base_record(self, **overrides):
        rec = {
            "mls_id": "MLS1",
            "address": "123 Main Street",
            "city": "Los Angeles",
            "price": 500000.0,
            "sqft": 1800.0,
            "source": "mls",
            "normalised_at": "2024-01-01T00:00:00",
        }
        rec.update(overrides)
        return rec

    def test_unique_records_all_kept(self, dedup):
        records = [
            self._base_record(mls_id="MLS1", address="1 Alpha Street"),
            self._base_record(mls_id="MLS2", address="2 Beta Street"),
        ]
        result, removed = dedup.deduplicate(records)
        assert removed == 0
        assert len(result) == 2

    def test_mls_id_duplicate_removed(self, dedup):
        records = [
            self._base_record(mls_id="MLS99", address="1 Alpha Street"),
            self._base_record(mls_id="MLS99", address="1 Alpha Street", price=510000.0),
        ]
        result, removed = dedup.deduplicate(records)
        assert removed == 1

    def test_address_duplicate_removed(self, dedup):
        records = [
            {"address": "100 Oak Avenue", "city": "Chicago", "price": 300000.0,
             "normalised_at": "2024-01-01T00:00:00"},
            {"address": "100 Oak Avenue", "city": "Chicago", "price": 305000.0,
             "normalised_at": "2024-01-02T00:00:00"},
        ]
        result, removed = dedup.deduplicate(records)
        assert removed == 1

    def test_merge_fills_missing_field(self):
        dedup = Deduplicator(merge=True)
        records = [
            {"mls_id": "MLS5", "address": "5 Elm Street", "city": "X",
             "price": None, "sqft": 2000.0, "normalised_at": "2024-01-01T00:00:00"},
            {"mls_id": "MLS5", "address": "5 Elm Street", "city": "X",
             "price": 400000.0, "sqft": None, "normalised_at": "2024-01-02T00:00:00"},
        ]
        result, removed = dedup.deduplicate(records)
        assert removed == 1
        merged = result[0]
        assert merged["price"] == 400000.0
        assert merged["sqft"] == 2000.0

    def test_no_merge_discards_duplicate(self):
        dedup = Deduplicator(merge=False)
        records = [
            {"mls_id": "MLS7", "address": "7 Pine Street", "city": "Y",
             "normalised_at": "2024-01-01T00:00:00"},
            {"mls_id": "MLS7", "address": "7 Pine Street", "city": "Y",
             "normalised_at": "2024-01-02T00:00:00"},
        ]
        result, removed = dedup.deduplicate(records)
        assert removed == 1
        assert len(result) == 1

    def test_empty_list(self, dedup):
        result, removed = dedup.deduplicate([])
        assert result == []
        assert removed == 0
