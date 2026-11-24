
-- ============================================================
-- 06_DATA_QUALITY.SQL
-- Purpose: Batch-scoped data quality checks
-- ============================================================

USE DATABASE SKYPOINTS_DB;

-- Update this value for each pipeline execution.
SET BATCH_ID = '3f3da9e4-b88e-440e-b43f-26ae0c855d2e';


-- ============================================================
-- 1. MEMBER DATA QUALITY SUMMARY
-- ============================================================

SELECT
    COUNT(*) AS TOTAL_MEMBER_RECORDS,

    COUNT_IF(
        VALIDATION_STATUS = 'ACCEPTED'
    ) AS ACCEPTED_RECORDS,

    COUNT_IF(
        VALIDATION_STATUS = 'REJECTED'
    ) AS REJECTED_RECORDS,

    COUNT_IF(
        VALIDATION_STATUS = 'ACCEPTED'
        AND MEMBER_NAME IS NULL
    ) AS MISSING_MEMBER_NAMES,

    COUNT_IF(
        VALIDATION_STATUS = 'ACCEPTED'
        AND SOURCE_MEMBER_ID IS NULL
    ) AS MISSING_SOURCE_MEMBER_IDS,

    COUNT_IF(
        VALIDATION_STATUS = 'ACCEPTED'
        AND QUERY_DATE IS NULL
    ) AS MISSING_QUERY_DATES,

    COUNT_IF(
        VALIDATION_STATUS = 'ACCEPTED'
        AND DOB > QUERY_DATE::DATE
    ) AS FUTURE_DOB_RECORDS

FROM SKYPOINTS_DB.STAGING.STG_MEMBER

WHERE BATCH_ID = $BATCH_ID;


-- ============================================================
-- 2. DUPLICATE MEMBER SOURCE IDS
-- Source IDs are unique within a country.
-- ============================================================

SELECT
    COUNTRY_CODE,
    SOURCE_MEMBER_ID,
    COUNT(*) AS DUPLICATE_COUNT

FROM SKYPOINTS_DB.STAGING.STG_MEMBER

WHERE BATCH_ID = $BATCH_ID
  AND VALIDATION_STATUS = 'ACCEPTED'

GROUP BY
    COUNTRY_CODE,
    SOURCE_MEMBER_ID

HAVING COUNT(*) > 1;


-- ============================================================
-- 3. INVALID MEMBER TIER CODES
-- Expected values: GLD, SLV, PLT
-- ============================================================

SELECT
    COUNTRY_CODE,
    SOURCE_MEMBER_ID,
    MEMBER_NAME,
    TIER_CODE

FROM SKYPOINTS_DB.STAGING.STG_MEMBER

WHERE BATCH_ID = $BATCH_ID
  AND VALIDATION_STATUS = 'ACCEPTED'
  AND TIER_CODE NOT IN ('GLD', 'SLV', 'PLT');


-- ============================================================
-- 4. INVALID MEMBER DATE CHRONOLOGY
-- Enrollment date should not be after flight date.
-- ============================================================

SELECT
    COUNTRY_CODE,
    SOURCE_MEMBER_ID,
    MEMBER_NAME,
    ENROLLMENT_DATE,
    FLIGHT_DATE

FROM SKYPOINTS_DB.STAGING.STG_MEMBER

WHERE BATCH_ID = $BATCH_ID
  AND VALIDATION_STATUS = 'ACCEPTED'
  AND ENROLLMENT_DATE IS NOT NULL
  AND FLIGHT_DATE IS NOT NULL
  AND ENROLLMENT_DATE > FLIGHT_DATE;


-- ============================================================
-- 5. INVALID AGE VALUES
-- ============================================================

SELECT
    COUNTRY_CODE,
    SOURCE_MEMBER_ID,
    MEMBER_NAME,
    DOB,
    AGE

FROM SKYPOINTS_DB.STAGING.STG_MEMBER

WHERE BATCH_ID = $BATCH_ID
  AND VALIDATION_STATUS = 'ACCEPTED'
  AND AGE < 0;


-- ============================================================
-- 6. LATEST RECORD UNIQUENESS
-- One current record per normalized member name.
-- ============================================================

SELECT
    UPPER(TRIM(MEMBER_NAME)) AS NORMALIZED_MEMBER_NAME,

    COUNT_IF(
        IS_LATEST_RECORD = TRUE
    ) AS LATEST_RECORD_COUNT,

    COUNT_IF(
        RECORD_STATUS = 'CURRENT'
    ) AS CURRENT_RECORD_COUNT

FROM SKYPOINTS_DB.STAGING.STG_MEMBER

WHERE BATCH_ID = $BATCH_ID
  AND VALIDATION_STATUS = 'ACCEPTED'
  AND MEMBER_NAME IS NOT NULL

GROUP BY UPPER(TRIM(MEMBER_NAME))

HAVING COUNT_IF(IS_LATEST_RECORD = TRUE) <> 1
    OR COUNT_IF(RECORD_STATUS = 'CURRENT') <> 1;


-- ============================================================
-- 7. REDEMPTION DATA QUALITY SUMMARY
-- ============================================================

SELECT
    COUNT(*) AS TOTAL_REDEMPTION_RECORDS,

    COUNT_IF(
        VALIDATION_STATUS = 'ACCEPTED'
    ) AS ACCEPTED_REDEMPTIONS,

    COUNT_IF(
        VALIDATION_STATUS = 'REJECTED'
    ) AS REJECTED_REDEMPTIONS,

    COUNT_IF(
        VALIDATION_STATUS = 'ACCEPTED'
        AND TRANSACTION_ID IS NULL
    ) AS MISSING_TRANSACTION_IDS,

    COUNT_IF(
        VALIDATION_STATUS = 'ACCEPTED'
        AND MEMBER_KEY IS NULL
    ) AS MISSING_MEMBER_KEYS,

    COUNT_IF(
        VALIDATION_STATUS = 'ACCEPTED'
        AND TRANSACTION_DATE IS NULL
    ) AS MISSING_TRANSACTION_DATES,

    COUNT_IF(
        VALIDATION_STATUS = 'ACCEPTED'
        AND MILES_REDEEMED < 0
    ) AS NEGATIVE_MILES

FROM SKYPOINTS_DB.STAGING.STG_REDEMPTION

WHERE BATCH_ID = $BATCH_ID;


-- ============================================================
-- 8. DUPLICATE REDEMPTION TRANSACTION IDS
-- ============================================================

SELECT
    COUNTRY_CODE,
    TRANSACTION_ID,
    COUNT(*) AS DUPLICATE_COUNT

FROM SKYPOINTS_DB.STAGING.STG_REDEMPTION

WHERE BATCH_ID = $BATCH_ID
  AND VALIDATION_STATUS = 'ACCEPTED'

GROUP BY
    COUNTRY_CODE,
    TRANSACTION_ID

HAVING COUNT(*) > 1;


-- ============================================================
-- 9. REDEMPTIONS WITHOUT A MATCHING CURRENT MEMBER
-- ============================================================

SELECT
    r.COUNTRY_CODE,
    r.TRANSACTION_ID,
    r.SOURCE_MEMBER_ID,
    r.MEMBER_KEY

FROM SKYPOINTS_DB.STAGING.STG_REDEMPTION r

LEFT JOIN SKYPOINTS_DB.STAGING.STG_MEMBER m
    ON r.BATCH_ID = m.BATCH_ID
    AND r.COUNTRY_CODE = m.COUNTRY_CODE
    AND r.MEMBER_KEY = m.SOURCE_MEMBER_ID
    AND m.VALIDATION_STATUS = 'ACCEPTED'
    AND m.IS_LATEST_RECORD = TRUE
    AND m.RECORD_STATUS = 'CURRENT'

WHERE r.BATCH_ID = $BATCH_ID
  AND r.VALIDATION_STATUS = 'ACCEPTED'
  AND m.SOURCE_MEMBER_ID IS NULL;


-- ============================================================
-- 10. FACT TABLE QUALITY SUMMARY
-- ============================================================

SELECT
    COUNT(*) AS TOTAL_FACT_RECORDS,

    COUNT(DISTINCT TRANSACTION_ID) AS UNIQUE_TRANSACTIONS,

    COALESCE(
        SUM(MILES_REDEEMED),
        0
    ) AS TOTAL_MILES,

    COUNT_IF(
        MEMBER_NAME IS NULL
    ) AS MISSING_MEMBER_NAMES,

    COUNT_IF(
        GLOBAL_MEMBER_ID IS NULL
    ) AS MISSING_GLOBAL_IDS,

    COUNT_IF(
        MILES_REDEEMED < 0
    ) AS NEGATIVE_MILES

FROM SKYPOINTS_DB.MART.FACT_REDEMPTION

WHERE BATCH_ID = $BATCH_ID;


-- ============================================================
-- 11. REJECTED MEMBER RECORD DETAILS
-- ============================================================

SELECT
    COUNTRY_CODE,
    SOURCE_ID,
    SOURCE_MEMBER_ID,
    MEMBER_NAME,
    REJECTION_REASONS

FROM SKYPOINTS_DB.STAGING.STG_MEMBER

WHERE BATCH_ID = $BATCH_ID
  AND VALIDATION_STATUS = 'REJECTED';


-- ============================================================
-- 12. REJECTED REDEMPTION RECORD DETAILS
-- ============================================================

SELECT
    COUNTRY_CODE,
    TRANSACTION_ID,
    SOURCE_MEMBER_ID,
    MEMBER_KEY,
    REJECTION_REASONS

FROM SKYPOINTS_DB.STAGING.STG_REDEMPTION

WHERE BATCH_ID = $BATCH_ID
  AND VALIDATION_STATUS = 'REJECTED';


-- ============================================================
-- END OF DATA QUALITY CHECKS
-- ============================================================
