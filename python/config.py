
COUNTRY_CONFIG = {
    "IND": {
        "member_file": "IND.csv",
        "redemption_file": "IND_redemptions.json",
        "target_table": "IND_MEMBERS",

        "column_mapping": {
            "source_id": "ID",
            "member_name": "Name",
            "dob": "DOB",
            "tier_code": "TierCode",
            "enrollment_date": "EnrollmentDate",
            "flight_date": "Flight Date",
            "member_type": "Individual or Corporate"
        },

        "date_formats": [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y%m%d"
        ]
    },

    "AUS": {
        "member_file": "AUS.xlsx",
        "redemption_file": "AUS_redemptions.json",
        "target_table": "AUS_MEMBERS",

        "column_mapping": {
            "source_id": "Unique ID",
            "member_name": "Member Name",
            "dob": "Date of Birth",
            "tier_code": "Tier Type",
            "enrollment_date": "Date of Enrollment",
            "flight_date": "Date of Flight"
        },

        "date_formats": [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y%m%d"
        ]
    },

    "USA": {
        "member_file": "USA.xlsx",
        "redemption_file": "USA_redemptions.json",
        "target_table": "USA_MEMBERS",

        "column_mapping": {
            "source_id": "ID",
            "member_name": "Name",
            "tier_code": "TierCode",
            "enrollment_date": "EnrollmentDate",
            "flight_date": "FlightDate"
        },

        "date_formats": [
            "%m%d%Y",
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y%m%d"
        ]
    }
}
