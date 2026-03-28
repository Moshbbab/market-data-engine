"""
Tests for the Data Normalizer.
"""

import pytest
from datetime import date
from src.cleaning.normalizer import DataNormalizer


@pytest.fixture
def normalizer():
    return DataNormalizer()


@pytest.fixture
def raw_mls_record():
    return {
        "mls_id": "MLS100",
        "address": "123  main st",
        "city": "los angeles",
        "list_price": "550,000",
        "sq_ft": "1800",
        "beds": "3",
        "baths": "2",
        "year_built": "2005",
        "list_date": "2024-03-15",
        "property_type": "SFR",
        "status": "Active",
        "source": "mls",
    }


@pytest.fixture
def raw_public_record():
    return {
        "parcel_id": "APN-999",
        "address": "456 Oak Ave",
        "owner": "Jane Smith",
        "assessed_value": 480000,
        "tax_amount": 6000,
        "year_built": 2001,
        "lot_size": 5000,
        "source": "public_records",
    }


class TestFieldAliasRenaming:
    def test_list_price_renamed_to_price(self, normalizer, raw_mls_record):
        result = normalizer.normalize([raw_mls_record])[0]
        assert "price" in result

    def test_sq_ft_renamed_to_sqft(self, normalizer, raw_mls_record):
        result = normalizer.normalize([raw_mls_record])[0]
        assert "sqft" in result

    def test_beds_renamed_to_bedrooms(self, normalizer, raw_mls_record):
        result = normalizer.normalize([raw_mls_record])[0]
        assert "bedrooms" in result

    def test_baths_renamed_to_bathrooms(self, normalizer, raw_mls_record):
        result = normalizer.normalize([raw_mls_record])[0]
        assert "bathrooms" in result


class TestTypeCoercion:
    def test_price_parsed_from_string_with_comma(self, normalizer, raw_mls_record):
        result = normalizer.normalize([raw_mls_record])[0]
        assert result["price"] == 550000.0

    def test_sqft_parsed_from_string(self, normalizer, raw_mls_record):
        result = normalizer.normalize([raw_mls_record])[0]
        assert result["sqft"] == 1800.0

    def test_bedrooms_parsed_as_int(self, normalizer, raw_mls_record):
        result = normalizer.normalize([raw_mls_record])[0]
        assert result["bedrooms"] == 3

    def test_year_built_parsed_as_int(self, normalizer, raw_mls_record):
        result = normalizer.normalize([raw_mls_record])[0]
        assert result["year_built"] == 2005

    def test_list_date_parsed_to_date(self, normalizer, raw_mls_record):
        result = normalizer.normalize([raw_mls_record])[0]
        assert result["list_date"] == date(2024, 3, 15)

    def test_int_lot_size_preserved(self, normalizer, raw_public_record):
        result = normalizer.normalize([raw_public_record])[0]
        assert result["lot_size"] == 5000.0


class TestControlledVocabularies:
    def test_sfr_mapped_to_single_family(self, normalizer, raw_mls_record):
        result = normalizer.normalize([raw_mls_record])[0]
        assert result["property_type"] == "single_family"

    def test_active_status_lowercase_mapped(self, normalizer, raw_mls_record):
        result = normalizer.normalize([raw_mls_record])[0]
        assert result["status"] == "active"

    def test_sold_status_mapped(self, normalizer):
        record = {"address": "1 A St", "status": "Closed"}
        result = normalizer.normalize([record])[0]
        assert result["status"] == "sold"


class TestAddressNormalisation:
    def test_address_title_cased(self, normalizer, raw_mls_record):
        result = normalizer.normalize([raw_mls_record])[0]
        # After title-casing, each word should start with an uppercase letter
        words = result["address"].split()
        assert all(w[0].isupper() for w in words if w and w[0].isalpha())

    def test_extra_whitespace_collapsed(self, normalizer):
        record = {"address": "  42   Elm   Street  "}
        result = normalizer.normalize([record])[0]
        assert "  " not in result["address"]


class TestMetadata:
    def test_normalised_at_added(self, normalizer, raw_mls_record):
        result = normalizer.normalize([raw_mls_record])[0]
        assert "normalised_at" in result

    def test_batch_normalisation_returns_all(self, normalizer):
        records = [
            {"address": "1 A St", "price": 100000},
            {"address": "2 B Ave", "price": 200000},
        ]
        results = normalizer.normalize(records)
        assert len(results) == 2
