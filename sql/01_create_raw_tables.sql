
-- =========================================================
-- 01. RAW LAYER
-- Purpose: Store source data with minimal transformation
-- =========================================================

-- Raw member feed
USE DATABASE SKYPOINTS_DB;
USE SCHEMA RAW;

CREATE TABLE IF NOT EXISTS RAW_MEMBER_FEED (

    BATCH_ID            VARCHAR(100) NOT NULL,
    SOURCE_FILE         VARCHAR(500) NOT NULL,
    SOURCE_ROW_NUMBER   NUMBER(10,0),

    COUNTRY_CODE        VARCHAR(3) NOT NULL,

    SOURCE_ID           VARCHAR(100),
    SOURCE_MEMBER_ID    VARCHAR(120),

    MEMBER_NAME_RAW     VARCHAR(1000),
    DOB_RAW             VARCHAR(100),
    TIER_CODE_RAW       VARCHAR(100),
    ENROLLMENT_DATE_RAW VARCHAR(100),
    FLIGHT_DATE_RAW     VARCHAR(100),
    MEMBER_TYPE_RAW     VARCHAR(100),
    POST_CODE_RAW       VARCHAR(100),

    -- Original source record retained for traceability
    RAW_RECORD          VARIANT,

    INGESTED_AT         TIMESTAMP_NTZ
                        DEFAULT CURRENT_TIMESTAMP()
);


-- Raw redemption JSON feed
CREATE TABLE IF NOT EXISTS RAW_REDEMPTION_FEED (

    BATCH_ID            VARCHAR(100) NOT NULL,
    SOURCE_FILE         VARCHAR(500) NOT NULL,

    COUNTRY_CODE        VARCHAR(3) NOT NULL,
    SOURCE_MEMBER_ID    VARCHAR(120),

    -- Complete original JSON payload
    PAYLOAD             VARIANT NOT NULL,

    INGESTED_AT         TIMESTAMP_NTZ
                        DEFAULT CURRENT_TIMESTAMP()
);
