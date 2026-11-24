
from pathlib import Path
from datetime import date
import pandas as pd

from config import COUNTRY_CONFIG

from ingestion import (
    ingest_member_files,
    ingest_redemption_json
)

from transformation import transform_members
from json_processor import flatten_redemptions

from snowflake_connection import get_snowflake_connection

from snowflake_loader import (
    load_member_records,
    load_redemption_feeds,
    load_staging_member_records,
    load_staging_redemption_records,
    load_country_member_tables,
    load_fact_redemptions,
    generate_batch_id
)


# --------------------------------------------------
# PROJECT CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

AS_OF_DATE = date.today()


# --------------------------------------------------
# OUTPUT UTILITIES
# --------------------------------------------------

def save_dataframe(df, filename):

    output_path = OUTPUT_DIR / filename

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    print(f"Generated: {output_path}")

    return output_path


# --------------------------------------------------
# STEP 1: MEMBER DATA INGESTION
# --------------------------------------------------

def process_member_data():

    print("\nSTEP 1: INGESTING MEMBER PROFILE FILES")

    raw_members = ingest_member_files(DATA_DIR)

    if raw_members is None or raw_members.empty:
        raise ValueError("No member records were ingested.")

    save_dataframe(raw_members, "raw_members.csv")

    print(f"Total member records: {len(raw_members)}")

    return raw_members


# --------------------------------------------------
# STEP 2: MEMBER DATA TRANSFORMATION
# --------------------------------------------------

def process_member_transformations(raw_members):

    print("\nSTEP 2: VALIDATING AND TRANSFORMING MEMBERS")

    accepted_members, rejected_members = transform_members(
        raw_members,
        AS_OF_DATE
    )

    save_dataframe(
        accepted_members,
        "member_staging.csv"
    )

    save_dataframe(
        rejected_members,
        "member_quarantine.csv"
    )

    print(f"Accepted members: {len(accepted_members)}")
    print(f"Rejected members: {len(rejected_members)}")

    if (
        not accepted_members.empty
        and "RECORD_STATUS" in accepted_members.columns
    ):

        current_count = (
            accepted_members["RECORD_STATUS"] == "CURRENT"
        ).sum()

        superseded_count = (
            accepted_members["RECORD_STATUS"] == "SUPERSEDED"
        ).sum()

        print(f"Current member records: {current_count}")
        print(f"Superseded member records: {superseded_count}")

    return accepted_members, rejected_members


# --------------------------------------------------
# STEP 3: COUNTRY-WISE MEMBER OUTPUT
# --------------------------------------------------

def process_country_outputs(accepted_members):

    print("\nSTEP 3: GENERATING COUNTRY-WISE MEMBER FILES")

    if accepted_members.empty:
        print("No valid members available for country outputs.")
        return

    if "IS_LATEST_RECORD" not in accepted_members.columns:
        raise ValueError(
            "IS_LATEST_RECORD column missing. "
            "Check transformation.py."
        )

    latest_members = accepted_members[
        accepted_members["IS_LATEST_RECORD"] == True
    ].copy()

    if latest_members.empty:
        print("No latest member records available.")
        return

    for country, config in COUNTRY_CONFIG.items():

        country_members = latest_members[
            latest_members["COUNTRY_CODE"] == country
        ].copy()

        if country_members.empty:
            print(f"No current records found for {country}.")
            continue

        target_table = config["target_table"]
        filename = f"{target_table.lower()}.csv"

        save_dataframe(country_members, filename)

        print(
            f"{country}: {len(country_members)} "
            f"current member records generated. "
            f"Target table: {target_table}"
        )


# --------------------------------------------------
# STEP 4: REDEMPTION INGESTION AND FLATTENING
# --------------------------------------------------

def process_redemption_data(redemption_data):

    print("\nSTEP 4: INGESTING REDEMPTION JSON FEEDS")

    if not redemption_data:
        print("No redemption JSON files found.")
        return pd.DataFrame()

    redemption_df = flatten_redemptions(redemption_data)

    if redemption_df is None or redemption_df.empty:
        print("No redemption transactions found.")
        return pd.DataFrame()

    accepted_redemptions = redemption_df[
        redemption_df["VALIDATION_STATUS"] == "ACCEPTED"
    ].copy()

    rejected_redemptions = redemption_df[
        redemption_df["VALIDATION_STATUS"] == "REJECTED"
    ].copy()

    save_dataframe(
        accepted_redemptions,
        "redemption_staging.csv"
    )

    save_dataframe(
        rejected_redemptions,
        "redemption_quarantine.csv"
    )

    print(f"Total redemption transactions: {len(redemption_df)}")
    print(f"Accepted redemption transactions: {len(accepted_redemptions)}")
    print(f"Rejected redemption transactions: {len(rejected_redemptions)}")

    return redemption_df


# --------------------------------------------------
# STEP 5: SNOWFLAKE RAW, STAGING AND MART LOADING
# --------------------------------------------------

def load_data_to_snowflake(
    raw_members,
    redemption_data,
    accepted_members,
    rejected_members,
    redemption_df,
    batch_id
):

    print("\nSTEP 5: LOADING DATA INTO SNOWFLAKE")

    connection = None

    try:

        connection = get_snowflake_connection()

        print("Connected to Snowflake successfully.")

        # Load original member source records into RAW.
        member_count = load_member_records(
            connection,
            raw_members,
            batch_id
        )

        # Load original redemption JSON feeds into RAW.
        redemption_count = load_redemption_feeds(
            connection,
            redemption_data,
            batch_id
        )

        # Load accepted and rejected member records into STAGING.
        staging_member_count = load_staging_member_records(
            connection,
            accepted_members,
            rejected_members,
            batch_id
        )

        # Load flattened accepted and rejected redemptions into STAGING.
        staging_redemption_count = load_staging_redemption_records(
            connection,
            redemption_df,
            batch_id
        )

        # Refresh country-wise MART member tables.
        mart_counts = load_country_member_tables(
            connection,
            batch_id
        )

        # Enrich and merge accepted redemptions into FACT_REDEMPTION.
        fact_count = load_fact_redemptions(
            connection,
            batch_id
        )

        print("\nSNOWFLAKE LOADING SUMMARY")
        print(f"Batch ID: {batch_id}")
        print(f"RAW member records: {member_count}")
        print(f"RAW redemption feeds: {redemption_count}")
        print(f"STAGING member records: {staging_member_count}")
        print(f"STAGING redemption transactions: {staging_redemption_count}")
        print(f"MART fact redemption records merged: {fact_count}")

        print("\nMART TABLE SUMMARY")

        for country, count in mart_counts.items():
            target_table = COUNTRY_CONFIG[country]["target_table"]
            print(f"{target_table}: {count} records")

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if connection:
            connection.close()
            print("Snowflake connection closed.")


# --------------------------------------------------
# STEP 6: REDEMPTION AND MEMBER PROFILE JOIN
# --------------------------------------------------

def join_redemptions_with_members(
    redemption_df,
    accepted_members
):

    print("\nSTEP 6: JOINING REDEMPTIONS WITH MEMBER PROFILES")

    if redemption_df.empty:
        print("No redemption records available for joining.")
        return pd.DataFrame()

    accepted_redemptions = redemption_df[
        redemption_df["VALIDATION_STATUS"] == "ACCEPTED"
    ].copy()

    if accepted_redemptions.empty:
        print("No accepted redemption records available.")
        return pd.DataFrame()

    if accepted_members.empty:
        raise ValueError(
            "No accepted member profiles available for joining."
        )

    current_members = accepted_members[
        accepted_members["IS_LATEST_RECORD"] == True
    ].copy()

    if current_members.empty:
        raise ValueError(
            "No current member profiles available."
        )

    member_profiles = current_members.rename(
        columns={"source_id": "MEMBER_KEY"}
    )

    if "MEMBER_KEY" not in member_profiles.columns:
        raise ValueError(
            "MEMBER_KEY could not be created from source_id."
        )

    duplicate_keys = member_profiles.duplicated(
        subset=["COUNTRY_CODE", "MEMBER_KEY"],
        keep=False
    )

    if duplicate_keys.any():
        raise ValueError(
            "Duplicate country-member keys found in current "
            "member profiles. Cannot perform a many-to-one join."
        )

    joined_df = accepted_redemptions.merge(
        member_profiles,
        on=["COUNTRY_CODE", "MEMBER_KEY"],
        how="left",
        suffixes=("_REDEMPTION", "_MEMBER"),
        indicator=True,
        validate="many_to_one"
    )

    joined_df["MEMBER_MATCH_STATUS"] = joined_df[
        "_merge"
    ].map({
        "both": "MATCHED",
        "left_only": "UNMATCHED"
    })

    joined_df = joined_df.drop(columns=["_merge"])

    matched_df = joined_df[
        joined_df["MEMBER_MATCH_STATUS"] == "MATCHED"
    ].copy()

    unmatched_df = joined_df[
        joined_df["MEMBER_MATCH_STATUS"] == "UNMATCHED"
    ].copy()

    save_dataframe(joined_df, "redemption_member_join.csv")
    save_dataframe(unmatched_df, "redemption_unmatched.csv")

    print(f"Matched redemption records: {len(matched_df)}")
    print(f"Unmatched redemption records: {len(unmatched_df)}")

    return joined_df


# --------------------------------------------------
# STEP 7: EXECUTION SUMMARY
# --------------------------------------------------

def print_execution_summary(
    raw_members,
    accepted_members,
    rejected_members,
    redemption_df,
    joined_df
):

    print("\n" + "=" * 55)
    print("PIPELINE EXECUTION SUMMARY")
    print("=" * 55)

    print(f"Total members ingested : {len(raw_members)}")
    print(f"Valid members          : {len(accepted_members)}")
    print(f"Rejected members       : {len(rejected_members)}")

    if (
        not accepted_members.empty
        and "RECORD_STATUS" in accepted_members.columns
    ):

        current_count = (
            accepted_members["RECORD_STATUS"] == "CURRENT"
        ).sum()

        superseded_count = (
            accepted_members["RECORD_STATUS"] == "SUPERSEDED"
        ).sum()

        print(f"Current records        : {current_count}")
        print(f"Superseded records     : {superseded_count}")

    accepted_count = 0
    rejected_count = 0

    if not redemption_df.empty:

        accepted_count = (
            redemption_df["VALIDATION_STATUS"] == "ACCEPTED"
        ).sum()

        rejected_count = (
            redemption_df["VALIDATION_STATUS"] == "REJECTED"
        ).sum()

    print(f"Redemption transactions: {len(redemption_df)}")
    print(f"Accepted redemptions   : {accepted_count}")
    print(f"Rejected redemptions   : {rejected_count}")
    print(f"Joined records         : {len(joined_df)}")

    print("\nPipeline execution completed.")


# --------------------------------------------------
# MAIN PIPELINE
# --------------------------------------------------

def main():

    print("=" * 55)
    print("       SKYPOINTS DATA ENGINEERING PIPELINE")
    print("=" * 55)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    try:

        batch_id = generate_batch_id()

        print(f"\nBatch ID: {batch_id}")

        # STEP 1: Member ingestion.
        raw_members = process_member_data()

        # STEP 2: Member validation and transformation.
        accepted_members, rejected_members = (
            process_member_transformations(raw_members)
        )

        # STEP 3: Country-wise latest member outputs.
        process_country_outputs(accepted_members)

        # Read original redemption JSON feeds.
        redemption_data = ingest_redemption_json(DATA_DIR)

        # STEP 4: Flatten and validate redemption transactions.
        redemption_df = process_redemption_data(redemption_data)

        # STEP 5: Load RAW, STAGING, and MART into Snowflake.
        load_data_to_snowflake(
            raw_members,
            redemption_data,
            accepted_members,
            rejected_members,
            redemption_df,
            batch_id
        )

        # STEP 6: Join redemption transactions with member profiles.
        joined_df = join_redemptions_with_members(
            redemption_df,
            accepted_members
        )

        # STEP 7: Print execution summary.
        print_execution_summary(
            raw_members,
            accepted_members,
            rejected_members,
            redemption_df,
            joined_df
        )

    except Exception as error:

        print("\nPIPELINE EXECUTION FAILED")
        print(f"Error: {error}")

        raise


if __name__ == "__main__":
    main()
