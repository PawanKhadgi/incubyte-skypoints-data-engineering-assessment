
from datetime import datetime
import re

from config import COUNTRY_CONFIG


VALID_TIERS = {"GLD", "SLV", "PLT"}

MAX_MEMBER_NAME_LENGTH = 255
MAX_MEMBER_ID_LENGTH = 18


def has_value(value):
    if value is None:
        return False

    return str(value).strip().lower() not in {
        "", "nan", "nat", "none"
    }


def normalize_member_name(value):
    if not has_value(value):
        return ""

    return re.sub(
        r"\s+", " ", str(value).strip()
    ).casefold()


def parse_source_date(value, country_code):
    if not has_value(value):
        return None

    country = str(country_code).strip().upper()

    if country not in COUNTRY_CONFIG:
        return None

    formats = COUNTRY_CONFIG[country]["date_formats"]

    value = str(value).strip()

    for date_format in formats:
        try:
            return datetime.strptime(
                value, date_format
            ).date()
        except ValueError:
            continue

    return None


def validate_member(record):
    errors = []

    source_id = str(record.get("source_id") or "").strip()
    member_name = str(record.get("member_name") or "").strip()

    country = str(
        record.get("COUNTRY_CODE", "")
    ).strip().upper()

    # Mandatory field validation
    if not has_value(source_id):
        errors.append("MISSING_SOURCE_ID")

    if not has_value(member_name):
        errors.append("MISSING_MEMBER_NAME")

    if not has_value(record.get("enrollment_date")):
        errors.append("MISSING_ENROLLMENT_DATE")

    if not country:
        errors.append("MISSING_COUNTRY_CODE")

    # Validate original source ID length.
    # Remove the country prefix added during ingestion.
    original_source_id = source_id

    prefix = f"{country}_"

    if country and source_id.startswith(prefix):
        original_source_id = source_id[len(prefix):]

    if has_value(original_source_id):
        if len(original_source_id) > MAX_MEMBER_ID_LENGTH:
            errors.append("MEMBER_ID_EXCEEDS_MAX_LENGTH")

    # Validate member name length.
    if has_value(member_name):
        if len(member_name) > MAX_MEMBER_NAME_LENGTH:
            errors.append("MEMBER_NAME_EXCEEDS_MAX_LENGTH")

    # Date validation
    enrollment = parse_source_date(
        record.get("enrollment_date"), country
    )

    flight = parse_source_date(
        record.get("flight_date"), country
    )

    dob = parse_source_date(
        record.get("dob"), country
    )

    if has_value(record.get("enrollment_date")) and enrollment is None:
        errors.append("INVALID_ENROLLMENT_DATE")

    if has_value(record.get("flight_date")) and flight is None:
        errors.append("INVALID_FLIGHT_DATE")

    if has_value(record.get("dob")) and dob is None:
        errors.append("INVALID_DOB")

    # Tier validation
    tier = str(
        record.get("tier_code") or ""
    ).strip().upper()

    if tier and tier not in VALID_TIERS:
        errors.append("INVALID_TIER_CODE")

    # Date chronology validation
    if enrollment and flight and flight < enrollment:
        errors.append("FLIGHT_BEFORE_ENROLLMENT")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "enrollment_date": enrollment,
        "flight_date": flight,
        "dob": dob
    }
