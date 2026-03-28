"""
Tests for the Quality Scorer.
"""

import pytest
from datetime import date, timedelta
from src.validation.quality_scorer import QualityScorer, QualityReport


def _record(completeness=90.0, has_errors=False, list_date_offset_days=0):
    """Build a minimal annotated record for scoring."""
    rec = {
        "address": "1 Main Street",
        "price": 500000.0,
        "_completeness_score": completeness,
        "list_date": date.today() - timedelta(days=list_date_offset_days),
    }
    if has_errors:
        rec["_schema_errors"] = [{"field": "price", "message": "bad"}]
    return rec


class TestQualityScorer:
    @pytest.fixture
    def scorer(self):
        return QualityScorer(max_age_days=30)

    def test_returns_quality_report(self, scorer):
        records = [_record()]
        report = scorer.score(records)
        assert isinstance(report, QualityReport)

    def test_empty_records_returns_zero_score(self, scorer):
        report = scorer.score([])
        assert report.composite_score == 0.0
        assert "No records" in report.issues[0]

    def test_perfect_data_scores_near_100(self, scorer):
        records = [_record(completeness=100.0) for _ in range(10)]
        report = scorer.score(records, duplicates_removed=0, original_count=10)
        assert report.composite_score >= 85.0

    def test_invalid_records_lower_validity_score(self, scorer):
        good = [_record() for _ in range(8)]
        bad = [_record(has_errors=True) for _ in range(2)]
        report = scorer.score(good + bad)
        assert report.validity_score < 100.0

    def test_stale_data_lowers_timeliness(self, scorer):
        records = [_record(list_date_offset_days=60)]  # 60 days ago
        report = scorer.score(records)
        assert report.timeliness_score == 0.0

    def test_fresh_data_high_timeliness(self, scorer):
        records = [_record(list_date_offset_days=0)]  # today
        report = scorer.score(records)
        assert report.timeliness_score == 100.0

    def test_grade_a_for_high_score(self, scorer):
        records = [_record(completeness=100.0) for _ in range(10)]
        report = scorer.score(records, duplicates_removed=0, original_count=10)
        assert report.grade in ("A", "B")

    def test_issues_list_populated_for_low_scores(self, scorer):
        records = [_record(completeness=10.0, has_errors=True, list_date_offset_days=90)]
        report = scorer.score(records, duplicates_removed=5, original_count=10)
        assert len(report.issues) > 0
