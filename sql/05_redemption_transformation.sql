
-- ============================================================
-- 05_REDEMPTION_TRANSFORMATION.SQL
-- Purpose: Enrich and load redemption transactions
-- Source : STAGING.STG_REDEMPTION + STAGING.STG_MEMBER
-- Target : MART.FACT_REDEMPTION
-- ============================================================

USE DATABASE SKYPOINTS_DB;
USE SCHEMA MART;

-- Update this value for each pipeline execution.
SET BATCH_ID = '3f3da9e4-b88e-440e-b43f-26ae0c855d2e';


-- ============================================================
-- 1. PREVIEW ENRICHED REDEMPTION RECORDS
-- ============================================================

SELECT
    r.BATCH_ID,
    r.COUNTRY_CODE,
    r.TRANSACTION_ID,
    r.SOURCE_MEMBER_ID,
    r.MEMBER_KEY,

    m.GLOBAL_MEMBER_ID,
    m.MEMBER_NAME,
    m.TIER_CODE,

    r.TRANSACTION_DATE,
    r.PARTNER,
    r.MILES_REDEEMED,
    r.STATUS,
    r.QUERY_DATE

FROM SKYPOINTS_DB.STAGING.STG_REDEMPTION r

INNER JOIN SKYPOINTS_DB.STAGING.STG_MEMBER m
    ON r.BATCH_ID = m.BATCH_ID
    AND r.COUNTRY_CODE = m.COUNTRY_CODE
    AND r.MEMBER_KEY = m.SOURCE_MEMBER_ID

WHERE r.BATCH_ID = $BATCH_ID
  AND r.VALIDATION_STATUS = 'ACCEPTED'
  AND m.VALIDATION_STATUS = 'ACCEPTED'
  AND m.IS_LATEST_RECORD = TRUE
  AND m.RECORD_STATUS = 'CURRENT';


-- ============================================================
-- 2. MERGE ENRICHED RECORDS INTO FACT TABLE
-- ============================================================

MERGE INTO SKYPOINTS_DB.MART.FACT_REDEMPTION AS target

USING (

    SELECT
        r.BATCH_ID,
        r.COUNTRY_CODE,
        r.TRANSACTION_ID,
        r.SOURCE_MEMBER_ID,
        r.MEMBER_KEY,

        m.GLOBAL_MEMBER_ID,
        m.MEMBER_NAME,
        m.TIER_CODE,

        r.TRANSACTION_DATE,
        r.PARTNER,
        r.MILES_REDEEMED,
        r.STATUS,
        r.QUERY_DATE

    FROM SKYPOINTS_DB.STAGING.STG_REDEMPTION r

    INNER JOIN SKYPOINTS_DB.STAGING.STG_MEMBER m
        ON r.BATCH_ID = m.BATCH_ID
        AND r.COUNTRY_CODE = m.COUNTRY_CODE
        AND r.MEMBER_KEY = m.SOURCE_MEMBER_ID

    WHERE r.BATCH_ID = $BATCH_ID
      AND r.VALIDATION_STATUS = 'ACCEPTED'
      AND m.VALIDATION_STATUS = 'ACCEPTED'
      AND m.IS_LATEST_RECORD = TRUE
      AND m.RECORD_STATUS = 'CURRENT'

    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY
            r.BATCH_ID,
            r.COUNTRY_CODE,
            r.TRANSACTION_ID
        ORDER BY r.QUERY_DATE DESC
    ) = 1

) AS source

ON target.BATCH_ID = source.BATCH_ID
AND target.COUNTRY_CODE = source.COUNTRY_CODE
AND target.TRANSACTION_ID = source.TRANSACTION_ID


WHEN MATCHED THEN UPDATE SET

    target.SOURCE_MEMBER_ID = source.SOURCE_MEMBER_ID,
    target.MEMBER_KEY = source.MEMBER_KEY,
    target.GLOBAL_MEMBER_ID = source.GLOBAL_MEMBER_ID,
    target.MEMBER_NAME = source.MEMBER_NAME,
    target.TIER_CODE = source.TIER_CODE,
    target.TRANSACTION_DATE = source.TRANSACTION_DATE,
    target.PARTNER = source.PARTNER,
    target.MILES_REDEEMED = source.MILES_REDEEMED,
    target.STATUS = source.STATUS,
    target.QUERY_DATE = source.QUERY_DATE


WHEN NOT MATCHED THEN INSERT (
    BATCH_ID,
    COUNTRY_CODE,
    TRANSACTION_ID,
    SOURCE_MEMBER_ID,
    MEMBER_KEY,
    GLOBAL_MEMBER_ID,
    MEMBER_NAME,
    TIER_CODE,
    TRANSACTION_DATE,
    PARTNER,
    MILES_REDEEMED,
    STATUS,
    QUERY_DATE
)

VALUES (
    source.BATCH_ID,
    source.COUNTRY_CODE,
    source.TRANSACTION_ID,
    source.SOURCE_MEMBER_ID,
    source.MEMBER_KEY,
    source.GLOBAL_MEMBER_ID,
    source.MEMBER_NAME,
    source.TIER_CODE,
    source.TRANSACTION_DATE,
    source.PARTNER,
    source.MILES_REDEEMED,
    source.STATUS,
    source.QUERY_DATE
);


-- ============================================================
-- 3. VERIFY FACT TABLE LOAD
-- ============================================================

SELECT
    COUNTRY_CODE,
    COUNT(*) AS TRANSACTION_COUNT,
    COUNT(DISTINCT TRANSACTION_ID) AS UNIQUE_TRANSACTIONS,
    SUM(MILES_REDEEMED) AS TOTAL_MILES

FROM SKYPOINTS_DB.MART.FACT_REDEMPTION

WHERE BATCH_ID = $BATCH_ID

GROUP BY COUNTRY_CODE
ORDER BY COUNTRY_CODE;


-- ============================================================
-- END OF REDEMPTION TRANSFORMATION
-- ============================================================
