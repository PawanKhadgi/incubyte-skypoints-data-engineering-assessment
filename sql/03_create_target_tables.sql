
USE DATABASE SKYPOINTS_DB;

-- =========================================================
-- 03. MART LAYER
-- Purpose:
-- 1. Country-wise current member records
-- 2. Redemption transaction fact table
-- =========================================================

-- Country-wise member tables

CREATE TABLE IF NOT EXISTS SKYPOINTS_DB.MART.IND_MEMBERS
LIKE SKYPOINTS_DB.STAGING.STG_MEMBER;

CREATE TABLE IF NOT EXISTS SKYPOINTS_DB.MART.AUS_MEMBERS
LIKE SKYPOINTS_DB.STAGING.STG_MEMBER;

CREATE TABLE IF NOT EXISTS SKYPOINTS_DB.MART.USA_MEMBERS
LIKE SKYPOINTS_DB.STAGING.STG_MEMBER;


-- =========================================================
-- FACT REDEMPTION
-- =========================================================

CREATE TABLE IF NOT EXISTS SKYPOINTS_DB.MART.FACT_REDEMPTION (
    BATCH_ID            VARCHAR(100) NOT NULL,
    COUNTRY_CODE        VARCHAR(3) NOT NULL,
    TRANSACTION_ID      VARCHAR(120) NOT NULL,
    SOURCE_MEMBER_ID    VARCHAR(120),
    MEMBER_KEY          VARCHAR(150),
    GLOBAL_MEMBER_ID    VARCHAR(36),
    MEMBER_NAME         VARCHAR(255),
    TIER_CODE           VARCHAR(5),
    TRANSACTION_DATE    DATE,
    PARTNER             VARCHAR(255),
    MILES_REDEEMED      NUMBER(18,0),
    STATUS              VARCHAR(30),
    QUERY_DATE          TIMESTAMP_NTZ,
    INGESTED_AT         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
