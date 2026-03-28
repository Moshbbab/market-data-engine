"""
Cleaning Module
===============

Data cleaning and normalization components for the market data engine.

Exposes the core cleaning classes:
- DataNormalizer: Standardises field names, types, and formats
- Deduplicator:   Detects and removes duplicate records
- OutlierDetector: Identifies statistical outliers
- MissingDataHandler: Imputes or flags missing values
- DataCleaner: Unified façade that runs the full cleaning pipeline
"""

from .normalizer import DataNormalizer
from .deduplicator import Deduplicator
from .outlier_detector import OutlierDetector
from .missing_handler import MissingDataHandler
from .cleaner import DataCleaner

__all__ = [
    "DataNormalizer",
    "Deduplicator",
    "OutlierDetector",
    "MissingDataHandler",
    "DataCleaner",
]
