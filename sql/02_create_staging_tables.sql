USE DATABASE SKYPOINTS_DB;
USE SCHEMA RAW;

-- =========================================================
-- 02. STAGING LAYER
-- Purpose: Standardization, transformation and validation
-- =========================================================

USE DATABASE SKYPOINTS_DB;

-- =========================================================
-- MEMBER STAGING
-- =========================================================

CREATE TABLE IF NOT EXISTS STAGING.STG_MEMBER (

    BATCH_ID             VARCHAR(100) NOT NULL,
    COUNTRY_CODE         VARCHAR(3) NOT NULL,

    SOURCE_ID            VARCHAR(100),
    SOURCE_MEMBER_ID     VARCHAR(120),
    GLOBAL_MEMBER_ID     VARCHAR(36),

    MEMBER_NAME          VARCHAR(255),
    DOB                  DATE,
    TIER_CODE            VARCHAR(5),
    ENROLLMENT_DATE      DATE,
    FLIGHT_DATE          DATE,

    POST_CODE            VARCHAR(20),
    MEMBER_TYPE          VARCHAR(30),

    AGE                  NUMBER(3,0),
    STALE_MEMBER         BOOLEAN,

    SOURCE_UPDATED_AT    TIMESTAMP_NTZ,
    SOURCE_SEQUENCE      NUMBER(20,0),

    QUERY_DATE           TIMESTAMP_NTZ,
    INGESTED_AT          TIMESTAMP_NTZ
                         DEFAULT CURRENT_TIMESTAMP(),

    VALIDATION_STATUS    VARCHAR(20),
    REJECTION_REASONS    ARRAY,

    IS_LATEST_RECORD     BOOLEAN,
    RECORD_STATUS        VARCHAR(20),
    LATEST_RECORD_REASON VARCHAR(100)

);


-- =========================================================
-- REDEMPTION STAGING
-- Purpose: Store flattened and validated transactions
-- =========================================================

CREATE TABLE IF NOT EXISTS STAGING.STG_REDEMPTION (

    BATCH_ID             VARCHAR(100) NOT NULL,
    COUNTRY_CODE         VARCHAR(3) NOT NULL,

    SOURCE_MEMBER_ID     VARCHAR(120),
    MEMBER_KEY           VARCHAR(150),

    FEED_DATE            DATE,
    TRANSACTION_ID       VARCHAR(120),
    TRANSACTION_DATE     DATE,

    PARTNER              VARCHAR(255),
    MILES_REDEEMED       NUMBER(18,0),
    STATUS               VARCHAR(30),

    QUERY_DATE           TIMESTAMP_NTZ,
    INGESTED_AT          TIMESTAMP_NTZ
                         DEFAULT CURRENT_TIMESTAMP(),

    VALIDATION_STATUS    VARCHAR(20),
    REJECTION_REASONS    ARRAY

);


-- =========================================================
-- MEMBER IDENTITY MAPPING
-- Supports verified cross-country member identity
-- =========================================================

CREATE TABLE IF NOT EXISTS STAGING.MEMBER_IDENTITY_MAP (

    COUNTRY_CODE         VARCHAR(3) NOT NULL,
    SOURCE_MEMBER_ID     VARCHAR(120) NOT NULL,

    GLOBAL_MEMBER_ID     VARCHAR(36) NOT NULL,

    VALID_FROM           TIMESTAMP_NTZ,
    VALID_TO             TIMESTAMP_NTZ,

    IS_CURRENT           BOOLEAN DEFAULT TRUE,

    MAPPING_SOURCE       VARCHAR(100),
    APPROVED_BY          VARCHAR(100),

    CREATED_AT           TIMESTAMP_NTZ
                         DEFAULT CURRENT_TIMESTAMP()

);
