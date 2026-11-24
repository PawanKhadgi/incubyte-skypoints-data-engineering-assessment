
from datetime import date, datetime
from collections import Counter, defaultdict

import pandas as pd

from validation import (
    validate_member,
    normalize_member_name
)


# --------------------------------------------------
# UTILITY FUNCTIONS
# --------------------------------------------------

def normalize_key_value(value):
    """Normalize a key value and safely handle missing values."""

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    return str(value).strip().upper()


# --------------------------------------------------
# STEP 1: DERIVED FIELD CALCULATIONS
# --------------------------------------------------

def calculate_age(dob, as_of_date):
    """Calculate member age using DOB."""

    if dob is None:
        return None

    age = as_of_date.year - dob.year

    if (as_of_date.month, as_of_date.day) < (
        dob.month,
        dob.day
    ):
        age -= 1

    return age


def calculate_stale_member(flight_date, as_of_date):
    """
    Mark a member as stale if their last flight
    was more than 90 days before the processing date.
    """

    if flight_date is None:
        return None

    days_since_flight = (as_of_date - flight_date).days

    return days_since_flight > 90


# --------------------------------------------------
# STEP 2: DUPLICATE SOURCE ID VALIDATION
# --------------------------------------------------

def validate_duplicate_source_ids(records):
    """
    Identify duplicate source IDs within the same country.

    Missing country codes and source IDs are excluded.
    """

    source_keys = []

    for record in records:

        country = normalize_key_value(
            record.get("COUNTRY_CODE")
        )

        source_id = normalize_key_value(
            record.get("source_id")
        )

        if country and source_id:
            source_keys.append(
                (country, source_id)
            )

    return Counter(source_keys)


# --------------------------------------------------
# STEP 3: LATEST MEMBER RECORD SELECTION
# --------------------------------------------------

def select_latest_member_records(accepted_df):
    """
    Select the latest record for each normalized member name.

    Priority:
    1. Latest FLIGHT_DATE
    2. Latest ENROLLMENT_DATE
    3. COUNTRY_CODE and source_id as deterministic tie-breaker

    All valid records remain in staging.
    Only one record per member is marked CURRENT.
    """

    accepted_df = accepted_df.copy()

    if accepted_df.empty:

        accepted_df["IS_LATEST_RECORD"] = pd.Series(
            dtype=bool
        )

        accepted_df["RECORD_STATUS"] = pd.Series(
            dtype=str
        )

        accepted_df["LATEST_RECORD_REASON"] = pd.Series(
            dtype=str
        )

        return accepted_df

    accepted_df["IS_LATEST_RECORD"] = False
    accepted_df["RECORD_STATUS"] = "SUPERSEDED"
    accepted_df["LATEST_RECORD_REASON"] = ""

    member_groups = defaultdict(list)

    for index, row in accepted_df.iterrows():

        member_key = normalize_member_name(
            row.get("member_name")
        )

        if member_key:
            member_groups[member_key].append(index)

    for member_key, indexes in member_groups.items():

        latest_flight_date = max(
            (
                accepted_df.at[index, "FLIGHT_DATE"]
                or date.min
            )
            for index in indexes
        )

        flight_candidates = [
            index
            for index in indexes
            if (
                accepted_df.at[index, "FLIGHT_DATE"]
                or date.min
            ) == latest_flight_date
        ]

        latest_enrollment_date = max(
            (
                accepted_df.at[index, "ENROLLMENT_DATE"]
                or date.min
            )
            for index in flight_candidates
        )

        final_candidates = [
            index
            for index in flight_candidates
            if (
                accepted_df.at[index, "ENROLLMENT_DATE"]
                or date.min
            ) == latest_enrollment_date
        ]

        winner = min(
            final_candidates,
            key=lambda index: (
                normalize_key_value(
                    accepted_df.at[index, "COUNTRY_CODE"]
                ),
                normalize_key_value(
                    accepted_df.at[index, "source_id"]
                )
            )
        )

        accepted_df.at[
            winner,
            "IS_LATEST_RECORD"
        ] = True

        accepted_df.at[
            winner,
            "RECORD_STATUS"
        ] = "CURRENT"

        if len(indexes) == 1:
            reason = "ONLY_RECORD_FOR_MEMBER"

        elif len(flight_candidates) == 1:
            reason = "LATEST_FLIGHT_DATE"

        elif len(final_candidates) == 1:
            reason = "ENROLLMENT_DATE_TIE_BREAKER"

        else:
            reason = "COUNTRY_AND_SOURCE_ID_TIE_BREAKER"

        accepted_df.at[
            winner,
            "LATEST_RECORD_REASON"
        ] = reason

        for index in indexes:

            if index == winner:
                continue

            record_flight = (
                accepted_df.at[index, "FLIGHT_DATE"]
                or date.min
            )

            winner_flight = (
                accepted_df.at[winner, "FLIGHT_DATE"]
                or date.min
            )

            if record_flight < winner_flight:

                superseded_reason = "OLDER_FLIGHT_DATE"

            else:

                record_enrollment = (
                    accepted_df.at[index, "ENROLLMENT_DATE"]
                    or date.min
                )

                winner_enrollment = (
                    accepted_df.at[winner, "ENROLLMENT_DATE"]
                    or date.min
                )

                if record_enrollment < winner_enrollment:
                    superseded_reason = "OLDER_ENROLLMENT_DATE"

                else:
                    superseded_reason = "TIE_BREAKER"

            accepted_df.at[
                index,
                "LATEST_RECORD_REASON"
            ] = superseded_reason

    return accepted_df


# --------------------------------------------------
# STEP 4: MEMBER DATA TRANSFORMATION
# --------------------------------------------------

def transform_members(df, as_of_date):
    """
    Validate and transform member records.

    Outputs:
    - Accepted member records
    - Rejected member records

    Accepted records include derived fields and
    latest-record selection metadata.
    """

    accepted_records = []
    rejected_records = []

    query_date = datetime.now().replace(
        microsecond=0
    )

    raw_records = df.to_dict("records")

    source_id_counts = validate_duplicate_source_ids(
        raw_records
    )

    for record in raw_records:

        validation = validate_member(record)

        errors = validation["errors"].copy()

        country = normalize_key_value(
            record.get("COUNTRY_CODE")
        )

        source_id = normalize_key_value(
            record.get("source_id")
        )

        if (
            country
            and source_id
            and source_id_counts[(country, source_id)] > 1
        ):
            errors.append(
                "DUPLICATE_SOURCE_ID_WITHIN_COUNTRY"
            )

        # --------------------------------------------------
        # REJECT INVALID RECORDS
        # --------------------------------------------------

        if errors:

            record.pop("dob", None)
            record.pop("enrollment_date", None)
            record.pop("flight_date", None)

            record["REJECTION_REASONS"] = errors
            record["VALIDATION_STATUS"] = "REJECTED"
            record["QUERY_DATE"] = query_date

            rejected_records.append(record)

            continue

        # --------------------------------------------------
        # PARSED DATE VALUES
        # --------------------------------------------------

        dob = validation["dob"]
        enrollment = validation["enrollment_date"]
        flight = validation["flight_date"]

        record.pop("dob", None)
        record.pop("enrollment_date", None)
        record.pop("flight_date", None)

        record["DOB"] = dob
        record["ENROLLMENT_DATE"] = enrollment
        record["FLIGHT_DATE"] = flight

        # --------------------------------------------------
        # DERIVED FIELDS
        # --------------------------------------------------

        record["AGE"] = calculate_age(
            dob,
            as_of_date
        )

        record["STALE_MEMBER"] = calculate_stale_member(
            flight,
            as_of_date
        )

        record["GLOBAL_MEMBER_ID"] = None

        record["VALIDATION_STATUS"] = "ACCEPTED"
        record["QUERY_DATE"] = query_date

        accepted_records.append(record)

    # --------------------------------------------------
    # CREATE DATAFRAMES
    # --------------------------------------------------

    accepted_df = pd.DataFrame(
        accepted_records
    )

    rejected_df = pd.DataFrame(
        rejected_records
    )

    # --------------------------------------------------
    # APPLY LATEST-RECORD LOGIC
    # --------------------------------------------------

    accepted_df = select_latest_member_records(
        accepted_df
    )

    return accepted_df, rejected_df
