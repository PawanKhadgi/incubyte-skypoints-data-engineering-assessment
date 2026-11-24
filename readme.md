# SkyPoints Data Engineering Assessment

## Overview

SkyPoints is a multi-country airline loyalty data engineering pipeline that ingests member profile files and redemption JSON feeds, validates and transforms the data, and loads curated datasets into Snowflake.

The pipeline supports India (IND), Australia (AUS), and the United States (USA).

## Architecture

The solution follows a layered data processing approach:

1. **Source:** CSV, Excel, and JSON files.
2. **Python ingestion:** Reads and standardizes country-specific source formats.
3. **Validation and transformation:** Validates records, calculates member age and stale-member status, identifies duplicate records, and selects the latest member record.
4. **Quarantine:** Separates invalid records with rejection reasons.
5. **Snowflake RAW:** Stores original member records and redemption JSON payloads.
6. **Snowflake STAGING:** Stores validated and standardized member and redemption records.
7. **Snowflake MART:** Stores country-specific member tables and the enriched redemption fact table.
8. **Data quality:** SQL scripts validate record counts, data consistency, duplicate records, and redemption matching.

See `docs/architecture.md` for additional details.

## Project Structure

```text
incubyte/
├── data/
│   ├── IND.csv
│   ├── AUS.xlsx
│   ├── USA.xlsx
│   └── IND_redemptions.json
├── docs/
│   └── architecture.md
├── output/
│   ├── raw_members.csv
│   ├── member_staging.csv
│   ├── member_quarantine.csv
│   ├── ind_members.csv
│   ├── aus_members.csv
│   ├── usa_members.csv
│   ├── redemption_staging.csv
│   ├── redemption_quarantine.csv
│   ├── redemption_member_join.csv
│   └── redemption_unmatched.csv
├── python/
│   ├── config.py
│   ├── ingestion.py
│   ├── validation.py
│   ├── transformation.py
│   ├── json_processor.py
│   ├── main.py
│   ├── snowflake_connection.py
│   └── snowflake_loader.py
├── sql/
│   ├── 01_create_raw_tables.sql
│   ├── 02_create_staging_tables.sql
│   ├── 03_create_target_tables.sql
│   ├── 04_member_transformation.sql
│   ├── 05_redemption_transformation.sql
│   └── 06_data_quality.sql
├── test/
│   └── test_transformation.py
├── requirements.txt
└── readme.md
```

## Technology Stack

- Python 3.12
- Pandas
- Snowflake
- Snowflake Connector for Python
- SQL
- JSON, CSV, Excel
- Pytest
- python-dotenv

## Prerequisites

- Python 3.12
- Access to a Snowflake account
- A configured Snowflake warehouse, database, and schemas

## Setup

### 1. Clone or download the project

Navigate to the project directory:

```powershell
cd E:\incubyte
```

### 2. Create and activate a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure Snowflake credentials

Create a `.env` file in the project root:

```env
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=RAW
SNOWFLAKE_ROLE=your_role
```

Use your own Snowflake credentials. Do not commit the `.env` file.

### 5. Create Snowflake database objects

Execute the SQL scripts in the following order using a Snowflake worksheet:

```text
01_create_raw_tables.sql
02_create_staging_tables.sql
03_create_target_tables.sql
```

These scripts create the required RAW, STAGING, and MART objects.

## Running the Pipeline

From the project root, execute:

```powershell
python .\python\main.py
```

The pipeline performs:

1. Member file ingestion.
2. Member validation and transformation.
3. Age and stale-member calculations.
4. Latest-record selection.
5. Country-wise member output generation.
6. Redemption JSON ingestion and flattening.
7. Loading into Snowflake RAW and STAGING.
8. Loading country-specific MART member tables.
9. Redemption enrichment and FACT table loading.
10. Redemption-to-member matching.
11. Execution summary generation.

## SQL Validation

After a successful Python pipeline execution, update the `BATCH_ID` variable in the SQL scripts with the batch ID printed by the pipeline.

Execute:

```text
04_member_transformation.sql
05_redemption_transformation.sql
06_data_quality.sql
```

These scripts provide transformation reconciliation, redemption enrichment/MERGE logic, and data quality checks.

The Python pipeline already loads the redemption fact table. The redemption SQL MERGE script can be used for independent verification or recovery; it is not necessary to run it again for normal pipeline execution.

## Automated Tests


Run the automated test suite from the project root:

```bash
python -m pytest -v
```

The current test suite contains **6 passing tests** covering:

- Age calculation.
- Missing date of birth handling.
- Stale-member identification.
- Non-stale-member identification.
- Member ID maximum length validation (18 characters).
- Member Name maximum length validation (255 characters).

Python compilation can also be verified using:

```bash
python -m compileall -q ./python
```

## Assessment Execution Results

The current sample execution produced:

| Metric | Result |
|---|---:|
| Member records ingested | 9 |
| Accepted member records | 8 |
| Rejected member records | 1 |
| Current member records | 7 |
| Superseded member records | 1 |
| Redemption transactions | 2 |
| Accepted redemption transactions | 2 |
| Rejected redemption transactions | 0 |
| Matched redemption transactions | 2 |
| Unmatched redemption transactions | 0 |
| Total redeemed miles | 17,000 |

Country-wise current member records:

| Country | Current Members |
|---|---:|
| IND | 3 |
| AUS | 2 |
| USA | 2 |

The rejected member record was Jonnathan (`AUS_2`) because of an invalid enrollment date.

The automated test suite currently reports **6 passed**.

## Known Limitations and Assumptions

- Cross-country member identity is provisionally resolved using normalized member names because a reliable global member identifier was not supplied.
- `GLOBAL_MEMBER_ID` therefore remains NULL until an authoritative identity mapping is provided.
- Name-based identity matching can create false matches when different members share the same name.
- The sample redemption data contains an India feed; Australia and USA redemption feeds were not supplied.
- Some source attributes, such as USA date of birth and postal code mappings, are unavailable in the supplied data.
- The current country MART loading process refreshes the country tables for each execution. A production implementation should support controlled incremental loading and batch-safe recovery.
- The current automated tests focus on core transformation logic; ingestion, Snowflake integration, and end-to-end behavior require additional automated tests.

## Security

- Store Snowflake credentials only in `.env`.
- Never commit credentials or sensitive source data to version control.
- Review generated output files before sharing externally.

## Author

SkyPoints Data Engineering Assessment
