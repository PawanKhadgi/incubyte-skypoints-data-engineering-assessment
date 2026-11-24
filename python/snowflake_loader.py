
import json
import uuid
import pandas as pd

from config import COUNTRY_CONFIG


# --------------------------------------------------
# UTILITY FUNCTIONS
# --------------------------------------------------

def clean_value(value):
    """Convert missing values to None and other values to strings."""

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return str(value).strip()


def clean_scalar(value):
    """Preserve data types while converting NaN/NaT to None."""

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, TypeError):
            pass

    return value


def clean_rejection_reasons(value):
    """Return a JSON-serializable list of rejection reasons."""

    if value is None:
        return []

    if isinstance(value, (list, tuple)):
        return [
            str(reason)
            for reason in value
            if clean_value(reason) is not None
        ]

    try:
        if pd.isna(value):
            return []
    except (TypeError, ValueError):
        pass

    return [str(value)]


def generate_batch_id():
    return str(uuid.uuid4())


# --------------------------------------------------
# LOAD MEMBER RECORDS INTO RAW TABLE
# --------------------------------------------------

def load_member_records(connection, members_df, batch_id):

    if members_df is None or members_df.empty:
        print("No member records available for RAW loading.")
        return 0

    insert_query = """
        INSERT INTO SKYPOINTS_DB.RAW.RAW_MEMBER_FEED (
            BATCH_ID,
            SOURCE_FILE,
            SOURCE_ROW_NUMBER,
            COUNTRY_CODE,
            SOURCE_ID,
            SOURCE_MEMBER_ID,
            MEMBER_NAME_RAW,
            DOB_RAW,
            TIER_CODE_RAW,
            ENROLLMENT_DATE_RAW,
            FLIGHT_DATE_RAW,
            MEMBER_TYPE_RAW,
            POST_CODE_RAW,
            RAW_RECORD
        )
        SELECT
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            PARSE_JSON(%s)
    """

    records = []

    for country, config in COUNTRY_CONFIG.items():

        country_df = members_df[
            members_df["COUNTRY_CODE"] == country
        ]

        if country_df.empty:
            continue

        source_id_column = config["column_mapping"]["source_id"]

        for row_number, (_, row) in enumerate(
            country_df.iterrows(),
            start=1
        ):

            source_id = clean_value(row.get(source_id_column))
            source_member_id = clean_value(row.get("source_id"))

            raw_record = {
                key: clean_value(value)
                for key, value in row.to_dict().items()
            }

            records.append((
                batch_id,
                clean_value(row.get("SOURCE_FILE")),
                row_number,
                country,
                source_id,
                source_member_id,
                clean_value(row.get("member_name")),
                clean_value(row.get("dob")),
                clean_value(row.get("tier_code")),
                clean_value(row.get("enrollment_date")),
                clean_value(row.get("flight_date")),
                clean_value(row.get("member_type")),
                None,
                json.dumps(raw_record)
            ))

    if not records:
        return 0

    cursor = connection.cursor()

    try:
        for record in records:
            cursor.execute(insert_query, record)

        connection.commit()

        print(
            f"Successfully loaded {len(records)} "
            "member records into RAW_MEMBER_FEED."
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()

    return len(records)


# --------------------------------------------------
# LOAD REDEMPTION JSON INTO RAW TABLE
# --------------------------------------------------

def load_redemption_feeds(connection, redemption_feeds, batch_id):

    if not redemption_feeds:
        print("No redemption feeds available for RAW loading.")
        return 0

    insert_query = """
        INSERT INTO SKYPOINTS_DB.RAW.RAW_REDEMPTION_FEED (
            BATCH_ID,
            SOURCE_FILE,
            COUNTRY_CODE,
            SOURCE_MEMBER_ID,
            PAYLOAD
        )
        SELECT
            %s, %s, %s, %s, PARSE_JSON(%s)
    """

    records = []

    for feed in redemption_feeds:

        country = str(
            feed.get("country_code") or ""
        ).strip().upper()

        if country not in COUNTRY_CONFIG:
            raise ValueError(
                f"Unsupported redemption country: {country}"
            )

        member_id = clean_value(feed.get("member_id"))

        source_member_id = (
            f"{country}_{member_id}"
            if member_id
            else None
        )

        source_file = COUNTRY_CONFIG[country]["redemption_file"]

        payload = json.dumps(feed)

        records.append((
            batch_id,
            source_file,
            country,
            source_member_id,
            payload
        ))

    if not records:
        return 0

    cursor = connection.cursor()

    try:
        for record in records:
            cursor.execute(insert_query, record)

        connection.commit()

        print(
            f"Successfully loaded {len(records)} "
            "redemption feeds into RAW_REDEMPTION_FEED."
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()

    return len(records)


# --------------------------------------------------
# LOAD TRANSFORMED MEMBER RECORDS INTO STAGING
# --------------------------------------------------

def load_staging_member_records(
    connection,
    accepted_df,
    rejected_df,
    batch_id
):

    accepted_records = (
        accepted_df.to_dict("records")
        if accepted_df is not None and not accepted_df.empty
        else []
    )

    rejected_records = (
        rejected_df.to_dict("records")
        if rejected_df is not None and not rejected_df.empty
        else []
    )

    all_records = (
        [(record, "ACCEPTED") for record in accepted_records]
        + [(record, "REJECTED") for record in rejected_records]
    )

    if not all_records:
        print("No member records available for STAGING loading.")
        return 0

    insert_query = """
        INSERT INTO SKYPOINTS_DB.STAGING.STG_MEMBER (
            BATCH_ID,
            COUNTRY_CODE,
            SOURCE_ID,
            SOURCE_MEMBER_ID,
            GLOBAL_MEMBER_ID,
            MEMBER_NAME,
            DOB,
            TIER_CODE,
            ENROLLMENT_DATE,
            FLIGHT_DATE,
            POST_CODE,
            MEMBER_TYPE,
            AGE,
            STALE_MEMBER,
            SOURCE_UPDATED_AT,
            SOURCE_SEQUENCE,
            QUERY_DATE,
            VALIDATION_STATUS,
            REJECTION_REASONS,
            IS_LATEST_RECORD,
            RECORD_STATUS,
            LATEST_RECORD_REASON
        )
        SELECT
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            PARSE_JSON(%s),
            %s, %s, %s
    """

    records = []

    for record, status in all_records:

        country = str(
            record.get("COUNTRY_CODE") or ""
        ).strip().upper()

        if country not in COUNTRY_CONFIG:
            raise ValueError(
                f"Unsupported staging country: {country}"
            )

        source_id_column = (
            COUNTRY_CONFIG[country]["column_mapping"]["source_id"]
        )

        source_id = clean_value(
            record.get(source_id_column)
        )

        source_member_id = clean_value(
            record.get("source_id")
        )

        if status == "ACCEPTED":
            dob = clean_scalar(record.get("DOB"))
            enrollment_date = clean_scalar(
                record.get("ENROLLMENT_DATE")
            )
            flight_date = clean_scalar(
                record.get("FLIGHT_DATE")
            )
        else:
            dob = None
            enrollment_date = None
            flight_date = None

        rejection_reasons = clean_rejection_reasons(
            record.get("REJECTION_REASONS")
        )

        records.append((
            batch_id,
            country,
            source_id,
            source_member_id,
            clean_value(record.get("GLOBAL_MEMBER_ID")),
            clean_value(record.get("member_name")),
            dob,
            clean_value(record.get("tier_code")),
            enrollment_date,
            flight_date,
            clean_value(record.get("POST_CODE")),
            clean_value(record.get("member_type")),
            clean_scalar(record.get("AGE")) if status == "ACCEPTED" else None,
            clean_scalar(record.get("STALE_MEMBER")) if status == "ACCEPTED" else None,
            clean_scalar(record.get("SOURCE_UPDATED_AT")),
            clean_scalar(record.get("SOURCE_SEQUENCE")),
            clean_scalar(record.get("QUERY_DATE")),
            status,
            json.dumps(rejection_reasons, allow_nan=False),
            clean_scalar(record.get("IS_LATEST_RECORD")),
            clean_value(record.get("RECORD_STATUS")),
            clean_value(record.get("LATEST_RECORD_REASON"))
        ))

    cursor = connection.cursor()

    try:
        for record in records:
            cursor.execute(insert_query, record)

        connection.commit()

        print(
            f"Successfully loaded {len(records)} "
            "member records into STAGING.STG_MEMBER."
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()

    return len(records)


# --------------------------------------------------
# LOAD FLATTENED REDEMPTION RECORDS INTO STAGING
# --------------------------------------------------

def load_staging_redemption_records(
    connection,
    redemption_df,
    batch_id
):
    """Load accepted and rejected transactions into STAGING."""

    if redemption_df is None or redemption_df.empty:
        print("No redemption transactions available for STAGING loading.")
        return 0

    insert_query = """
        INSERT INTO SKYPOINTS_DB.STAGING.STG_REDEMPTION (
            BATCH_ID,
            COUNTRY_CODE,
            SOURCE_MEMBER_ID,
            MEMBER_KEY,
            FEED_DATE,
            TRANSACTION_ID,
            TRANSACTION_DATE,
            PARTNER,
            MILES_REDEEMED,
            STATUS,
            QUERY_DATE,
            VALIDATION_STATUS,
            REJECTION_REASONS
        )
        SELECT
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, PARSE_JSON(%s)
    """

    records = []

    for record in redemption_df.to_dict("records"):

        country = str(
            record.get("COUNTRY_CODE") or ""
        ).strip().upper()

        if country not in COUNTRY_CONFIG:
            raise ValueError(
                f"Unsupported redemption country: {country}"
            )

        rejection_reasons = clean_rejection_reasons(
            record.get("REJECTION_REASONS")
        )

        records.append((
            batch_id,
            country,
            clean_value(record.get("SOURCE_MEMBER_ID")),
            clean_value(record.get("MEMBER_KEY")),
            clean_scalar(record.get("FEED_DATE")),
            clean_value(record.get("TRANSACTION_ID")),
            clean_scalar(record.get("TRANSACTION_DATE")),
            clean_value(record.get("PARTNER")),
            clean_scalar(record.get("MILES_REDEEMED")),
            clean_value(record.get("STATUS")),
            clean_scalar(record.get("QUERY_DATE")),
            clean_value(record.get("VALIDATION_STATUS")),
            json.dumps(rejection_reasons, allow_nan=False)
        ))

    cursor = connection.cursor()

    try:
        for record in records:
            cursor.execute(insert_query, record)

        connection.commit()

        print(
            f"Successfully loaded {len(records)} "
            "redemption transactions into STAGING.STG_REDEMPTION."
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()

    return len(records)


# --------------------------------------------------
# REFRESH COUNTRY-WISE MART TABLES
# --------------------------------------------------

def load_country_member_tables(connection, batch_id):
    """
    Refresh country-wise MART tables using the supplied
    complete source batch.
    """

    target_columns = """
        BATCH_ID,
        COUNTRY_CODE,
        SOURCE_ID,
        SOURCE_MEMBER_ID,
        GLOBAL_MEMBER_ID,
        MEMBER_NAME,
        DOB,
        TIER_CODE,
        ENROLLMENT_DATE,
        FLIGHT_DATE,
        POST_CODE,
        MEMBER_TYPE,
        AGE,
        STALE_MEMBER,
        SOURCE_UPDATED_AT,
        SOURCE_SEQUENCE,
        QUERY_DATE,
        INGESTED_AT,
        VALIDATION_STATUS,
        REJECTION_REASONS,
        IS_LATEST_RECORD,
        RECORD_STATUS,
        LATEST_RECORD_REASON
    """

    cursor = connection.cursor()
    country_counts = {}

    try:
        cursor.execute("BEGIN")

        for country, config in COUNTRY_CONFIG.items():

            target_table = config["target_table"]

            if not target_table.replace("_", "").isalnum():
                raise ValueError(
                    f"Invalid target table name: {target_table}"
                )

            cursor.execute(
                f"""
                DELETE FROM SKYPOINTS_DB.MART.{target_table}
                """
            )

            insert_query = f"""
                INSERT INTO SKYPOINTS_DB.MART.{target_table} (
                    {target_columns}
                )
                SELECT
                    {target_columns}
                FROM SKYPOINTS_DB.STAGING.STG_MEMBER
                WHERE BATCH_ID = %s
                  AND COUNTRY_CODE = %s
                  AND VALIDATION_STATUS = 'ACCEPTED'
                  AND IS_LATEST_RECORD = TRUE
                  AND RECORD_STATUS = 'CURRENT'
            """

            cursor.execute(
                insert_query,
                (batch_id, country)
            )

            country_counts[country] = cursor.rowcount

        connection.commit()

        print("\nMART LOADING SUMMARY")

        for country, count in country_counts.items():
            print(
                f"{country}: {count} current member records "
                f"loaded into {COUNTRY_CONFIG[country]['target_table']}."
            )

        print("Country-wise MART tables refreshed successfully.")

        return country_counts

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()


# --------------------------------------------------
# LOAD ENRICHED REDEMPTIONS INTO MART FACT TABLE
# --------------------------------------------------

def load_fact_redemptions(connection, batch_id):
    """
    Enrich accepted redemption transactions with current member
    profiles and MERGE them into MART.FACT_REDEMPTION.

    Merge key:
    BATCH_ID + COUNTRY_CODE + TRANSACTION_ID
    """

    merge_query = """
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

            WHERE r.BATCH_ID = %s
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
        )
    """

    cursor = connection.cursor()

    try:
        cursor.execute(
            merge_query,
            (batch_id,)
        )

        affected_rows = cursor.rowcount

        connection.commit()

        print(
            f"Successfully merged {affected_rows} "
            "records into MART.FACT_REDEMPTION."
        )

        return affected_rows

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
