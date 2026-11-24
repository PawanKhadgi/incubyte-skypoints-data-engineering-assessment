
import sys
from pathlib import Path
from datetime import date

# Add the project's python folder to the import path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = PROJECT_ROOT / "python"

sys.path.insert(0, str(PYTHON_DIR))

from transformation import calculate_age, calculate_stale_member
from validation import validate_member


# --------------------------------------------------
# AGE CALCULATION TESTS
# --------------------------------------------------

def test_age_calculation():

    dob = date(1995, 5, 15)
    as_of_date = date(2025, 5, 15)

    result = calculate_age(dob, as_of_date)

    assert result == 30


def test_missing_dob():

    result = calculate_age(None, date(2025, 5, 15))

    assert result is None


# --------------------------------------------------
# STALE MEMBER TESTS
# --------------------------------------------------

def test_stale_member():

    flight_date = date(2025, 1, 1)
    as_of_date = date(2025, 4, 15)

    result = calculate_stale_member(flight_date, as_of_date)

    assert result is True


def test_non_stale_member():

    flight_date = date(2025, 3, 1)
    as_of_date = date(2025, 4, 15)

    result = calculate_stale_member(flight_date, as_of_date)

    assert result is False


# --------------------------------------------------
# MEMBER VALIDATION TESTS
# --------------------------------------------------

def test_member_id_exceeds_max_length():

    record = {
        "source_id": "IND_1234567890123456789",
        "member_name": "Pawan",
        "enrollment_date": "2024-01-01",
        "COUNTRY_CODE": "IND"
    }

    result = validate_member(record)

    assert result["valid"] is False
    assert "MEMBER_ID_EXCEEDS_MAX_LENGTH" in result["errors"]


def test_member_name_exceeds_max_length():

    record = {
        "source_id": "IND_1",
        "member_name": "A" * 256,
        "enrollment_date": "2024-01-01",
        "COUNTRY_CODE": "IND"
    }

    result = validate_member(record)

    assert result["valid"] is False
    assert "MEMBER_NAME_EXCEEDS_MAX_LENGTH" in result["errors"]
