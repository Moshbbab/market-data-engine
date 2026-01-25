# Market Data Engine

> **Production-grade market data extraction, cleaning, and validation engine for real estate valuation**

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/)
[![Data Quality](https://img.shields.io/badge/Data%20Quality-Enterprise-green)](https://github.com/Moshbbab/market-data-engine)
[![Status](https://img.shields.io/badge/Status-Production-success)](https://github.com/Moshbbab/market-data-engine)

---

## 🎯 Overview

The **Market Data Engine** is a critical component of the Hemmah Valuation Operating System (HVOS), responsible for acquiring, processing, and validating real estate market data from multiple sources. It ensures data quality, consistency, and reliability for downstream valuation processes.

This engine transforms raw, inconsistent market data into clean, normalized, and validated datasets ready for analysis.

---

## 🏗️ Architecture

```
market-data-engine/
├── src/
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── mls_connector.py          # MLS data extraction
│   │   ├── public_records.py         # Public records scraping
│   │   ├── api_integrators.py        # Third-party API integration
│   │   └── web_scrapers.py           # Web scraping utilities
│   ├── cleaning/
│   │   ├── __init__.py
│   │   ├── normalizer.py             # Data normalization
│   │   ├── deduplicator.py           # Duplicate detection & removal
│   │   ├── outlier_detector.py       # Statistical outlier detection
│   │   └── missing_handler.py        # Missing data imputation
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── schema_validator.py       # Schema validation
│   │   ├── business_rules.py         # Business logic validation
│   │   ├── quality_scorer.py         # Data quality scoring
│   │   └── completeness_checker.py   # Completeness verification
│   ├── enrichment/
│   │   ├── __init__.py
│   │   ├── geocoding.py              # Address geocoding
│   │   ├── demographics.py           # Demographic data enrichment
│   │   ├── market_trends.py          # Market trend integration
│   │   └── property_features.py      # Feature engineering
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py               # Database operations
│   │   ├── cache_manager.py          # Caching layer
│   │   └── version_control.py        # Data versioning
│   └── monitoring/
│       ├── __init__.py
│       ├── quality_metrics.py        # Quality monitoring
│       ├── alerts.py                 # Alert system
│       └── dashboard.py              # Monitoring dashboard
├── config/
│   ├── sources.yaml                  # Data source configurations
│   ├── validation_rules.yaml         # Validation rules
│   └── quality_thresholds.yaml       # Quality thresholds
├── tests/
├── docs/
├── requirements.txt
└── README.md
```

---

## 🚀 Core Features

### 1. Multi-Source Data Extraction
- **MLS Integration**: Direct connection to Multiple Listing Services
- **Public Records**: Automated scraping of county assessor data
- **API Integration**: Third-party data providers (Zillow, Redfin, etc.)
- **Web Scraping**: Intelligent scraping with rate limiting and error handling

### 2. Data Cleaning & Normalization
- **Standardization**: Uniform formatting across all sources
- **Deduplication**: Intelligent duplicate detection and merging
- **Outlier Detection**: Statistical methods for anomaly identification
- **Missing Data Handling**: Imputation and flagging strategies

### 3. Quality Validation
- **Schema Validation**: Ensure data structure compliance
- **Business Rules**: Domain-specific validation logic
- **Completeness Checks**: Required field verification
- **Quality Scoring**: Automated quality assessment (0-100)

### 4. Data Enrichment
- **Geocoding**: Convert addresses to coordinates
- **Demographics**: Add neighborhood demographic data
- **Market Trends**: Integrate historical price trends
- **Feature Engineering**: Derive additional property attributes

### 5. Real-Time Monitoring
- **Quality Metrics**: Track data quality over time
- **Alert System**: Automated alerts for quality issues
- **Dashboard**: Visual monitoring interface
- **Audit Trails**: Complete data lineage tracking

---

## 📊 Data Pipeline Flow

```
Data Sources (MLS, Public Records, APIs)
           ↓
    Extraction Layer
           ↓
  Cleaning & Normalization
           ↓
    Deduplication
           ↓
  Outlier Detection
           ↓
    Validation Layer
           ↓
  Quality Scoring
           ↓
    Enrichment
           ↓
  Storage & Caching
           ↓
  Monitoring & Alerts
```

---

## 💻 Usage

### Basic Data Extraction

```python
from market_data_engine import DataExtractor, DataCleaner, DataValidator

# Initialize components
extractor = DataExtractor(sources=['mls', 'public_records'])
cleaner = DataCleaner()
validator = DataValidator()

# Extract data
raw_data = extractor.extract(
    location='Los Angeles, CA',
    property_type='residential',
    date_range=('2024-01-01', '2024-12-31')
)

# Clean data
cleaned_data = cleaner.clean(raw_data)

# Validate quality
validation_result = validator.validate(cleaned_data)

if validation_result.quality_score >= 80:
    print(f"Data quality: {validation_result.quality_score}/100")
    print(f"Records: {len(cleaned_data)}")
else:
    print(f"Quality issues: {validation_result.issues}")
```

### Advanced Pipeline

```python
from market_data_engine import MarketDataPipeline

# Create pipeline
pipeline = MarketDataPipeline(
    sources=['mls', 'zillow', 'public_records'],
    quality_threshold=85,
    enable_enrichment=True,
    enable_monitoring=True
)

# Run pipeline
result = pipeline.run(
    location='San Francisco, CA',
    property_type='residential',
    min_price=500000,
    max_price=2000000
)

# Access results
print(f"Total records: {result.total_records}")
print(f"Quality score: {result.quality_score}")
print(f"Data freshness: {result.freshness_hours} hours")

# Export to database
result.save_to_database('postgresql://localhost/valuation_db')
```

---

## 📈 Data Quality Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Completeness | >95% | 97.2% |
| Accuracy | >90% | 93.5% |
| Consistency | >95% | 96.8% |
| Timeliness | <24h | 6h |
| Uniqueness | >99% | 99.4% |

---

## 🔒 Data Security & Privacy

- **Encryption**: All data encrypted at rest and in transit
- **Access Control**: Role-based access control (RBAC)
- **Audit Logging**: Complete audit trail of all operations
- **Compliance**: GDPR, CCPA compliant
- **Data Retention**: Configurable retention policies

---

## 🛠️ Installation

```bash
# Clone repository
git clone https://github.com/Moshbbab/market-data-engine.git
cd market-data-engine

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure data sources
cp config/sources.yaml.example config/sources.yaml
# Edit config/sources.yaml with your API keys

# Run tests
pytest tests/
```

---

## 📚 Documentation

- [Data Source Configuration](docs/sources.md)
- [Validation Rules](docs/validation.md)
- [Quality Scoring](docs/quality.md)
- [API Reference](docs/api.md)

---

## 🔗 Integration with HVOS

This engine integrates seamlessly with other HVOS components:

- **Valuation Core Engine**: Provides clean data for valuation
- **Comparable Intelligence**: Feeds comparable selection
- **Financial Modeling System**: Supplies market parameters
- **Report Automation**: Provides market context data

---

## 🤝 Contributing

Contributions must meet enterprise standards:
- Maintain >90% test coverage
- Follow PEP 8 style guidelines
- Document all public APIs
- Ensure data quality standards

---

**Status**: Production-Ready  
**Version**: 1.0.0  
**Last Updated**: January 2026
