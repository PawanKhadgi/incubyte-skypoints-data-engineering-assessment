# SkyPoints Data Pipeline Architecture

## 1. Architecture Overview

The SkyPoints solution uses Python for ingestion, validation, and transformation, with Snowflake providing persistent RAW, STAGING, and MART data layers.

The pipeline processes airline loyalty member profiles from India, Australia, and the United States, along with available redemption transaction feeds.

## 2. High-Level Data Flow

```text
Country Source Files
(CSV / Excel / JSON)
          |
          v
   Python Ingestion
          |
          v
 Standardization
          |
          v
 Validation and Transformation
          |
          +----------------------+
          |                      |
          v                      v
   Accepted Records       Rejected Records
          |                      |
          v                      v
 Member Transformations     Quarantine Output
          |
          v
   Snowflake RAW
          |
          v
 Snowflake STAGING
          |
          +----------------------+
          |                      |
          v                      v
 Country Member MART      Redemption Processing
          |                      |
          |                      v
          |               Redemption Fact MART
          |                      ^
          +------ Member Join ---+
          
          |
          v
   SQL Data Quality Checks
```

## 3. Source Systems

### Member profile feeds

| Country | Source Format | File |
|---|---|---|
| India | CSV | IND.csv |
| Australia | Excel | AUS.xlsx |
| United States | Excel | USA.xlsx |

### Redemption feeds

| Country | Source Format | File |
|---|---|---|
| India | JSON | IND_redemptions.json |
| Australia | Not supplied | Not available |
| United States | Not supplied | Not available |

## 4. Python Processing Layer

### Ingestion

`ingestion.py`

- Reads CSV and Excel member files.
- Applies country-specific source-column mappings.
- Standardizes source fields into a common structure.
- Creates country-prefixed member keys.
- Reads available redemption JSON feeds.

### Validation

`validation.py`

- Performs member data quality validation.
- Identifies invalid records.
- Captures rejection reasons for quarantine processing.

### Member transformation

`transformation.py`

- Calculates age using date of birth and the pipeline execution date.
- Identifies stale members based on the flight-date rule.
- Detects duplicate source identifiers within a country.
- Identifies the latest record for a member.
- Separates accepted and rejected records.

For cross-country records, normalized member names are currently used as a provisional identity matching key.

Latest-record selection prioritizes flight date, followed by enrollment date and deterministic tie-breakers.

### Redemption processing

`json_processor.py`

- Parses redemption JSON feeds.
- Flattens transaction-level information.
- Standardizes transaction attributes.
- Validates transaction identifiers, dates, member references, and miles.
- Separates accepted and rejected transactions.

## 5. Snowflake Data Architecture

Database: `SKYPOINTS_DB`

### RAW schema

Purpose: Preserve source data for traceability.

Tables:

- `RAW_MEMBER_FEED`
- `RAW_REDEMPTION_FEED`

Original member attributes and redemption JSON payloads are stored with batch and source metadata.

### STAGING schema

Purpose: Store standardized and validated data.

Tables:

- `STG_MEMBER`
- `STG_REDEMPTION`
- `MEMBER_IDENTITY_MAP`

The member staging layer includes validation status, rejection reasons, calculated attributes, and latest-record indicators.

The identity mapping table is designed to support an authoritative cross-country identity mapping when available.

### MART schema

Purpose: Provide curated member and redemption datasets.

Tables:

- `IND_MEMBERS`
- `AUS_MEMBERS`
- `USA_MEMBERS`
- `FACT_REDEMPTION`

The country tables contain current accepted member records.

The redemption fact table contains accepted redemption transactions enriched with member attributes.

## 6. Redemption-to-Member Matching

Redemption records are matched to current member profiles using:

- `COUNTRY_CODE`
- Country-prefixed member key

The matching process identifies matched and unmatched transactions.

The fact table also stores the member name and tier information when a valid member match exists.

## 7. Batch Processing and Auditability

Each execution generates a unique batch ID.

The batch ID is used to associate source records, staging records, and fact records with a particular execution.

`QUERY_DATE` captures the processing/audit timestamp used by the transformation logic.

The pipeline preserves rejected records and their validation reasons for review.

## 8. Data Quality and Reconciliation

SQL scripts provide validation and reconciliation checks:

| Script | Responsibility |
|---|---|
| 01_create_raw_tables.sql | Create RAW tables |
| 02_create_staging_tables.sql | Create STAGING tables |
| 03_create_target_tables.sql | Create MART tables |
| 04_member_transformation.sql | Member transformation reconciliation |
| 05_redemption_transformation.sql | Redemption enrichment and MERGE |
| 06_data_quality.sql | Data quality validation |

Checks include:

- Accepted and rejected record counts.
- Missing required attributes.
- Age and stale-member calculation consistency.
- Duplicate member and transaction identifiers.
- Latest-record uniqueness.
- Redemption-to-member matching.
- Fact table totals and miles reconciliation.

## 9. Design Assumptions and Limitations

1. The supplied source data does not provide a reliable global member identifier.
2. Normalized member names are used provisionally to identify cross-country records. This can cause false matches if different people share a name.
3. `GLOBAL_MEMBER_ID` remains NULL until an approved identity mapping is available.
4. Redemption feeds are available only for India in the supplied assessment data.
5. Source attributes unavailable in the input files are not fabricated.
6. The current country MART loading implementation refreshes the country tables. Production deployment should use a batch-safe incremental or controlled snapshot strategy.
7. Python owns the operational ingestion and transformation flow. The SQL scripts provide Snowflake-side reconciliation, enrichment, and data quality validation.

## 10. Future Enhancements

- Implement authoritative global member identity resolution.
- Add automated integration tests for ingestion and Snowflake loading.
- Introduce incremental, idempotent country MART loading.
- Add orchestration, monitoring, and alerting.
- Expand redemption processing as additional country feeds become available.
- Add schema evolution and stronger source-to-target reconciliation.
