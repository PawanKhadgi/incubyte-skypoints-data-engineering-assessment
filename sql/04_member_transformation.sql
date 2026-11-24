
-- ============================================================
-- 04_MEMBER_TRANSFORMATION.SQL
-- Purpose: Member transformation reconciliation
-- Source : STAGING.STG_MEMBER
-- Owner  : Python transformation pipeline
-- ============================================================

USE DATABASE SKYPOINTS_DB;
USE SCHEMA STAGING;

-- Update this value for each pipeline execution.
SET BATCH_ID = '3f3da9e4-b88e-440e-b43f-26ae0c855d2e';


-- ============================================================
-- 1. MEMBER TRANSFORMATION SUMMARY
-- ============================================================

SELECT
    COUNTRY_CODE,
    VALIDATION_STATUS,
    RECORD_STATUS,
    COUNT(*) AS RECORD_COUNT
FROM SKYPOINTS_DB.STAGING.STG_MEMBER
WHERE BATCH_ID = $BATCH_ID
GROUP BY
    COUNTRY_CODE,
    VALIDATION_STATUS,
    RECORD_STATUS
ORDER BY
    COUNTRY_CODE,
    VALIDATION_STATUS,
    RECORD_STATUS;


-- ============================================================
-- 2. VERIFY AGE CALCULATION
-- Age = year difference adjusted for whether birthday passed.
-- ============================================================

SELECT
    COUNTRY_CODE,
    SOURCE_MEMBER_ID,
    MEMBER_NAME,
    DOB,
    AGE AS PYTHON_AGE,

    DATEDIFF(
        YEAR,
        DOB,
        QUERY_DATE::DATE
    )
    -
    IFF(
        TO_CHAR(QUERY_DATE::DATE, 'MMDD')
            < TO_CHAR(DOB, 'MMDD'),
        1,
        0
    ) AS EXPECTED_AGE

FROM SKYPOINTS_DB.STAGING.STG_MEMBER

WHERE BATCH_ID = $BATCH_ID
  AND VALIDATION_STATUS = 'ACCEPTED'
  AND DOB IS NOT NULL
  AND QUERY_DATE IS NOT NULL

  AND AGE <> (
      DATEDIFF(
          YEAR,
          DOB,
          QUERY_DATE::DATE
      )
      -
      IFF(
          TO_CHAR(QUERY_DATE::DATE, 'MMDD')
              < TO_CHAR(DOB, 'MMDD'),
          1,
          0
      )
  );


-- ============================================================
-- 3. VERIFY STALE MEMBER CALCULATION
-- Stale = more than 90 days since last flight.
-- ============================================================

SELECT
    COUNTRY_CODE,
    SOURCE_MEMBER_ID,
    MEMBER_NAME,
    FLIGHT_DATE,
    QUERY_DATE::DATE AS AS_OF_DATE,
    STALE_MEMBER AS PYTHON_STALE_FLAG,

    DATEDIFF(
        DAY,
        FLIGHT_DATE,
        QUERY_DATE::DATE
    ) > 90 AS EXPECTED_STALE_FLAG

FROM SKYPOINTS_DB.STAGING.STG_MEMBER

WHERE BATCH_ID = $BATCH_ID
  AND VALIDATION_STATUS = 'ACCEPTED'
  AND FLIGHT_DATE IS NOT NULL
  AND QUERY_DATE IS NOT NULL

  AND STALE_MEMBER IS DISTINCT FROM (
      DATEDIFF(
          DAY,
          FLIGHT_DATE,
          QUERY_DATE::DATE
      ) > 90
  );


-- ============================================================
-- 4. VERIFY LATEST RECORD SELECTION
-- One current record per normalized member name.
-- ============================================================

SELECT
    UPPER(TRIM(MEMBER_NAME)) AS NORMALIZED_MEMBER_NAME,
    COUNT_IF(IS_LATEST_RECORD = TRUE) AS LATEST_RECORD_COUNT,
    COUNT_IF(RECORD_STATUS = 'CURRENT') AS CURRENT_RECORD_COUNT

FROM SKYPOINTS_DB.STAGING.STG_MEMBER

WHERE BATCH_ID = $BATCH_ID
  AND VALIDATION_STATUS = 'ACCEPTED'
  AND MEMBER_NAME IS NOT NULL

GROUP BY UPPER(TRIM(MEMBER_NAME))

HAVING COUNT_IF(IS_LATEST_RECORD = TRUE) > 1
    OR COUNT_IF(RECORD_STATUS = 'CURRENT') > 1;


-- ============================================================
-- 5. VERIFY COUNTRY-WISE MART COUNTS
-- ============================================================

SELECT
    'IND' AS COUNTRY_CODE,
    COUNT(*) AS MART_RECORD_COUNT
FROM SKYPOINTS_DB.MART.IND_MEMBERS
WHERE BATCH_ID = $BATCH_ID

UNION ALL

SELECT
    'AUS',
    COUNT(*)
FROM SKYPOINTS_DB.MART.AUS_MEMBERS
WHERE BATCH_ID = $BATCH_ID

UNION ALL

SELECT
    'USA',
    COUNT(*)
FROM SKYPOINTS_DB.MART.USA_MEMBERS
WHERE BATCH_ID = $BATCH_ID;


-- ============================================================
-- END OF MEMBER TRANSFORMATION RECONCILIATION
-- ============================================================
