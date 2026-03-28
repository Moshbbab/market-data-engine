"""
Tests for the DataCleaner unified pipeline.
"""

import pytest
from src.cleaning.cleaner import DataCleaner, CleaningResult


def _raw_records():
    return [
        {
            "mls_id": "MLS001",
            "address": "1 Alpha Street",
            "city": "Chicago",
            "list_price": "300,000",
            "sq_ft": "1500",
            "beds": "3",
            "baths": "2",
            "year_built": "2010",
            "list_date": "2024-06-01",
            "property_type": "SFR",
            "status": "Active",
            "source": "mls",
        },
        {
            "mls_id": "MLS002",
            "address": "2 Beta Avenue",
            "city": "Chicago",
            "list_price": "420,000",
            "sq_ft": "2000",
            "beds": "4",
            "baths": "3",
            "year_built": "2015",
            "list_date": "2024-07-10",
            "property_type": "SFR",
            "status": "Active",
            "source": "mls",
        },
        # Duplicate
        {
            "mls_id": "MLS001",
            "address": "1 Alpha Street",
            "city": "Chicago",
            "list_price": "305,000",
            "source": "public_records",
        },
    ]


class TestDataCleaner:
    @pytest.fixture
    def cleaner(self):
        return DataCleaner()

    def test_returns_cleaning_result(self, cleaner):
        result = cleaner.clean(_raw_records())
        assert isinstance(result, CleaningResult)

    def test_input_count_correct(self, cleaner):
        result = cleaner.clean(_raw_records())
        assert result.input_count == 3

    def test_duplicate_removed(self, cleaner):
        result = cleaner.clean(_raw_records())
        assert result.duplicates_removed >= 1

    def test_output_count_less_than_input(self, cleaner):
        result = cleaner.clean(_raw_records())
        assert result.output_count <= result.input_count

    def test_retention_rate_between_0_and_1(self, cleaner):
        result = cleaner.clean(_raw_records())
        assert 0.0 <= result.retention_rate <= 1.0

    def test_records_list_populated(self, cleaner):
        result = cleaner.clean(_raw_records())
        assert len(result.records) == result.output_count

    def test_prices_are_floats_after_cleaning(self, cleaner):
        result = cleaner.clean(_raw_records())
        for record in result.records:
            price = record.get("price")
            if price is not None:
                assert isinstance(price, float)

    def test_empty_input(self, cleaner):
        result = cleaner.clean([])
        assert result.input_count == 0
        assert result.output_count == 0
        assert result.records == []
