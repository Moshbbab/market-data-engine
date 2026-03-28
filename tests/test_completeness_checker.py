"""
Tests for the Completeness Checker.
"""

import pytest
from src.validation.completeness_checker import CompletenessChecker


class TestCompletenessChecker:
    @pytest.fixture
    def checker(self):
        return CompletenessChecker(threshold=70.0)

    def _full_record(self):
        from datetime import date
        return {
            "address": "1 Main Street",
            "price": 500000.0,
            "sqft": 1800.0,
            "bedrooms": 3,
            "bathrooms": 2.0,
            "year_built": 2005,
            "property_type": "single_family",
            "status": "active",
            "lot_size": 5000.0,
            "list_date": date(2024, 1, 15),
        }

    def test_full_record_scores_100(self, checker):
        record = self._full_record()
        score = checker.score_record(record)
        assert score == 100.0

    def test_missing_half_scores_50(self, checker):
        record = {
            "address": "1 Main Street",
            "price": 500000.0,
            "sqft": 1800.0,
            "bedrooms": 3,
            "bathrooms": 2.0,
        }
        score = checker.score_record(record)
        assert score == 50.0

    def test_empty_record_scores_0(self, checker):
        score = checker.score_record({})
        assert score == 0.0

    def test_check_annotates_records(self, checker):
        records = [self._full_record()]
        annotated, summary = checker.check(records)
        assert "_completeness_score" in annotated[0]
        assert "_missing_key_fields" in annotated[0]

    def test_summary_contains_expected_keys(self, checker):
        records = [self._full_record()]
        _, summary = checker.check(records)
        assert "total_records" in summary
        assert "average_completeness" in summary
        assert "complete_records" in summary

    def test_complete_count_correct(self, checker):
        full = self._full_record()
        partial = {"address": "2 B St"}
        records = [full, partial]
        _, summary = checker.check(records)
        assert summary["complete_records"] == 1
        assert summary["incomplete_records"] == 1

    def test_empty_input(self, checker):
        annotated, summary = checker.check([])
        assert annotated == []
        assert summary["average_completeness"] == 0.0
