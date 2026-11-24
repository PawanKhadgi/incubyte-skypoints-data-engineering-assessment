
from datetime import datetime
import math
import pandas as pd


# --------------------------------------------------
# DATE VALIDATION
# --------------------------------------------------

def parse_redemption_date(value):
    """Parse supported redemption date formats."""

    if value is None or str(value).strip() == "":
        return None

    value = str(value).strip()

    formats = [
        "%Y%m%d",
        "%Y-%m-%d"
    ]

    for date_format in formats:
        try:
            return datetime.strptime(
                value,
                date_format
            ).date()
        except ValueError:
            continue

    return None


# --------------------------------------------------
# MILES VALIDATION
# --------------------------------------------------

def parse_miles(value):
    """Parse miles as a finite, non-negative integer."""

    if value is None or str(value).strip() == "":
        return None

    if isinstance(value, bool):
        return None

    try:
        miles = float(value)

        if not math.isfinite(miles):
            return None

        if not miles.is_integer():
            return None

        return int(miles)

    except (ValueError, TypeError, OverflowError):
        return None


# --------------------------------------------------
# REDEMPTION JSON FLATTENING
# --------------------------------------------------

def flatten_redemptions(json_data):
    """
    Process country-wise redemption feeds.

    Supports:
    - A single country JSON object.
    - A list of country JSON objects.

    Generates a country-specific MEMBER_KEY.
    """

    if isinstance(json_data, dict):
        json_records = [json_data]

    elif isinstance(json_data, list):
        json_records = json_data

    else:
        raise ValueError(
            "Redemption JSON must contain an object or list."
        )

    query_date = datetime.now().replace(
        microsecond=0
    )

    flattened_records = []

    for feed in json_records:

        if not isinstance(feed, dict):
            raise ValueError(
                "Each redemption feed must be a JSON object."
            )

        member_id = feed.get("member_id")

        country_code = str(
            feed.get("country_code") or ""
        ).strip().upper()

        feed_date_raw = feed.get("feed_date")

        feed_date = parse_redemption_date(
            feed_date_raw
        )

        redemptions = feed.get(
            "redemptions",
            []
        )

        if not isinstance(redemptions, list):
            raise ValueError(
                "'redemptions' must contain a JSON array."
            )

        # Build country-specific member key.
        member_key = (
            f"{country_code}_{str(member_id).strip()}"
            if country_code
            and member_id is not None
            and str(member_id).strip()
            else None
        )

        for transaction in redemptions:

            errors = []

            if not isinstance(transaction, dict):

                flattened_records.append({
                    "COUNTRY_CODE": country_code or None,
                    "SOURCE_MEMBER_ID": member_id,
                    "MEMBER_KEY": member_key,
                    "FEED_DATE": feed_date,
                    "TRANSACTION_ID": None,
                    "TRANSACTION_DATE": None,
                    "PARTNER": None,
                    "MILES_REDEEMED": None,
                    "STATUS": None,
                    "QUERY_DATE": query_date,
                    "VALIDATION_STATUS": "REJECTED",
                    "REJECTION_REASONS": "INVALID_TRANSACTION_OBJECT"
                })

                continue

            transaction_id = transaction.get("txn_id")
            transaction_date_raw = transaction.get("txn_date")
            partner = transaction.get("partner")
            miles_raw = transaction.get("miles_redeemed")
            status = transaction.get("status")

            # --------------------------------------------------
            # MEMBER VALIDATION
            # --------------------------------------------------

            if member_id is None or str(member_id).strip() == "":
                errors.append("MISSING_MEMBER_ID")

            if not country_code:
                errors.append("MISSING_COUNTRY_CODE")

            # --------------------------------------------------
            # FEED DATE VALIDATION
            # --------------------------------------------------

            if feed_date_raw is None or str(feed_date_raw).strip() == "":
                errors.append("MISSING_FEED_DATE")

            elif feed_date is None:
                errors.append("INVALID_FEED_DATE")

            # --------------------------------------------------
            # TRANSACTION ID VALIDATION
            # --------------------------------------------------

            if transaction_id is None or str(transaction_id).strip() == "":
                errors.append("MISSING_TRANSACTION_ID")

            else:
                transaction_id = str(transaction_id).strip()

            # --------------------------------------------------
            # TRANSACTION DATE VALIDATION
            # --------------------------------------------------

            transaction_date = parse_redemption_date(
                transaction_date_raw
            )

            if transaction_date_raw is None or str(transaction_date_raw).strip() == "":
                errors.append("MISSING_TRANSACTION_DATE")

            elif transaction_date is None:
                errors.append("INVALID_TRANSACTION_DATE")

            # --------------------------------------------------
            # MILES VALIDATION
            # --------------------------------------------------

            miles_redeemed = parse_miles(miles_raw)

            if miles_raw is None or str(miles_raw).strip() == "":
                errors.append("MISSING_MILES_REDEEMED")

            elif miles_redeemed is None:
                errors.append("INVALID_MILES_REDEEMED")

            elif miles_redeemed < 0:
                errors.append("NEGATIVE_MILES_REDEEMED")

            # --------------------------------------------------
            # BUILD FLATTENED RECORD
            # --------------------------------------------------

            record = {
                "COUNTRY_CODE": country_code or None,
                "SOURCE_MEMBER_ID": member_id,
                "MEMBER_KEY": member_key,
                "FEED_DATE": feed_date,
                "TRANSACTION_ID": transaction_id,
                "TRANSACTION_DATE": transaction_date,
                "PARTNER": partner,
                "MILES_REDEEMED": miles_redeemed,
                "STATUS": status,
                "QUERY_DATE": query_date,
                "VALIDATION_STATUS": (
                    "ACCEPTED" if not errors else "REJECTED"
                ),
                "REJECTION_REASONS": (
                    " | ".join(errors) if errors else None
                )
            }

            flattened_records.append(record)

    columns = [
        "COUNTRY_CODE",
        "SOURCE_MEMBER_ID",
        "MEMBER_KEY",
        "FEED_DATE",
        "TRANSACTION_ID",
        "TRANSACTION_DATE",
        "PARTNER",
        "MILES_REDEEMED",
        "STATUS",
        "QUERY_DATE",
        "VALIDATION_STATUS",
        "REJECTION_REASONS"
    ]

    result = pd.DataFrame(
        flattened_records,
        columns=columns
    )

    # --------------------------------------------------
    # DUPLICATE TRANSACTION VALIDATION
    # --------------------------------------------------

    # Transaction IDs are checked within the same country.
    # All occurrences of a duplicate ID are rejected.
    # Records without a country or transaction ID are excluded
    # from duplicate detection.

    valid_keys = (
        result["COUNTRY_CODE"].notna()
        & result["COUNTRY_CODE"].astype(str).str.strip().ne("")
        & result["TRANSACTION_ID"].notna()
        & result["TRANSACTION_ID"].astype(str).str.strip().ne("")
    )

    duplicate_mask = result.loc[valid_keys].duplicated(
        subset=["COUNTRY_CODE", "TRANSACTION_ID"],
        keep=False
    )

    duplicate_indices = result.loc[valid_keys].index[
        duplicate_mask
    ]

    for index in duplicate_indices:

        result.at[index, "VALIDATION_STATUS"] = "REJECTED"

        existing_reason = result.at[
            index,
            "REJECTION_REASONS"
        ]

        if pd.notna(existing_reason) and existing_reason:
            result.at[index, "REJECTION_REASONS"] = (
                existing_reason + " | DUPLICATE_TRANSACTION_ID"
            )
        else:
            result.at[index, "REJECTION_REASONS"] = (
                "DUPLICATE_TRANSACTION_ID"
            )

    return result
