"""
Integration tests for the MarketDataPipeline.
"""

import pytest
from src.pipeline import MarketDataPipeline, PipelineResult


class TestMarketDataPipeline:
    @pytest.fixture
    def pipeline(self):
        return MarketDataPipeline(
            sources=["mls", "public_records"],
            quality_threshold=0.0,  # Accept any quality for integration tests
        )

    def test_run_returns_pipeline_result(self, pipeline):
        result = pipeline.run(location="Los Angeles, CA")
        assert isinstance(result, PipelineResult)

    def test_total_records_non_negative(self, pipeline):
        result = pipeline.run(location="San Francisco, CA")
        assert result.total_records >= 0

    def test_quality_score_in_range(self, pipeline):
        result = pipeline.run(location="Chicago, IL")
        assert 0.0 <= result.quality_score <= 100.0

    def test_freshness_hours_non_negative(self, pipeline):
        result = pipeline.run(location="New York, NY")
        assert result.freshness_hours >= 0.0

    def test_extraction_results_populated(self, pipeline):
        result = pipeline.run(location="Austin, TX")
        assert len(result.extraction_results) > 0

    def test_location_stored(self, pipeline):
        result = pipeline.run(location="Denver, CO")
        assert result.location == "Denver, CO"

    def test_property_type_stored(self, pipeline):
        result = pipeline.run(location="Seattle, WA", property_type="condo")
        assert result.property_type == "condo"

    def test_with_price_filters(self, pipeline):
        result = pipeline.run(
            location="Miami, FL",
            min_price=200000.0,
            max_price=1_000_000.0,
        )
        assert isinstance(result, PipelineResult)
