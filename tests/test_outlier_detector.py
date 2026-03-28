"""
Tests for the Outlier Detector.
"""

import pytest
from src.cleaning.outlier_detector import OutlierDetector


def _make_records(prices):
    """Create minimal records with the given price values."""
    return [{"address": f"{i} St", "price": p, "sqft": 1500.0} for i, p in enumerate(prices)]


class TestOutlierDetectorIQR:
    @pytest.fixture
    def detector(self):
        return OutlierDetector(method="iqr")

    def test_no_outliers_in_uniform_data(self, detector):
        records = _make_records([300000, 310000, 305000, 308000, 302000, 307000])
        result = detector.detect(records)
        assert all(not r.get("_is_outlier") for r in result)

    def test_extreme_high_price_flagged(self, detector):
        records = _make_records([300000, 310000, 305000, 308000, 302000, 10_000_000])
        result = detector.detect(records)
        outliers = [r for r in result if r.get("_is_outlier")]
        assert len(outliers) >= 1
        assert any("price" in r.get("_outlier_fields", set()) for r in outliers)

    def test_too_few_records_skipped(self, detector):
        records = _make_records([100000, 200000, 300000])  # < 4
        result = detector.detect(records)
        assert all(not r.get("_is_outlier") for r in result)

    def test_price_per_sqft_derived_and_checked(self, detector):
        records = [
            {"address": "1 A", "price": 300000, "sqft": 1500},
            {"address": "2 B", "price": 310000, "sqft": 1500},
            {"address": "3 C", "price": 305000, "sqft": 1500},
            {"address": "4 D", "price": 308000, "sqft": 1500},
            {"address": "5 E", "price": 302000, "sqft": 1500},
            {"address": "6 F", "price": 50_000_000, "sqft": 100},  # absurd ppsf
        ]
        result = detector.detect(records)
        outliers = [r for r in result if r.get("_is_outlier")]
        assert len(outliers) >= 1


class TestOutlierDetectorZScore:
    @pytest.fixture
    def detector(self):
        return OutlierDetector(method="zscore", z_thresh=2.0)

    def test_zscore_flags_extreme_value(self, detector):
        records = _make_records([100, 101, 99, 100, 102, 100, 101, 1_000_000])
        result = detector.detect(records)
        outliers = [r for r in result if r.get("_is_outlier")]
        assert len(outliers) >= 1


class TestOutlierDetectorBoth:
    def test_both_methods(self):
        detector = OutlierDetector(method="both")
        records = _make_records([300000, 310000, 305000, 308000, 302000, 50_000_000])
        result = detector.detect(records)
        outliers = [r for r in result if r.get("_is_outlier")]
        assert len(outliers) >= 1

    def test_empty_records(self):
        detector = OutlierDetector()
        result = detector.detect([])
        assert result == []
