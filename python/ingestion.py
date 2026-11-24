
import json
import pandas as pd
from pathlib import Path

from config import COUNTRY_CONFIG


def read_input_file(file_path):
    with open(file_path, "rb") as file:
        signature = file.read(4)

    if signature.startswith(b"PK"):
        print("Detected Excel workbook format.")
        return pd.read_excel(
            file_path,
            dtype=str,
            engine="openpyxl"
        )

    print("Detected CSV text format.")

    for encoding in ["utf-8-sig", "cp1252", "latin1"]:
        try:
            return pd.read_csv(
                file_path,
                dtype=str,
                encoding=encoding
            )
        except UnicodeDecodeError:
            continue

    raise ValueError(f"Unable to decode input file: {file_path}")


def standardize_member_columns(df, country):
    if country not in COUNTRY_CONFIG:
        raise ValueError(f"Unsupported country code: {country}")

    mapping = COUNTRY_CONFIG[country]["column_mapping"]

    result = df.copy()

    for canonical_name, source_name in mapping.items():
        if source_name in df.columns:
            result[canonical_name] = (
                df[source_name]
                .fillna("")
                .astype(str)
                .str.strip()
            )
        else:
            result[canonical_name] = ""

    result["source_id"] = result["source_id"].apply(
        lambda value: f"{country}_{value}" if value else ""
    )

    result["COUNTRY_CODE"] = country

    return result


def ingest_member_files(data_dir):
    all_members = []

    for country, config in COUNTRY_CONFIG.items():

        filename = config["member_file"]
        file_path = Path(data_dir) / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Input file not found: {file_path}"
            )

        print(f"\nReading {filename}...")

        df = read_input_file(file_path)

        print(f"Loaded {len(df)} records from {filename}")
        print(f"Original columns: {list(df.columns)}")

        df = standardize_member_columns(df, country)

        df["SOURCE_FILE"] = filename

        all_members.append(df)

        print(f"Standardized columns for {country}.")

    combined_df = pd.concat(
        all_members,
        ignore_index=True,
        sort=False
    )

    print(
        f"\nTotal member records ingested: {len(combined_df)}"
    )

    return combined_df


def ingest_redemption_json(data_dir):
    all_redemptions = []

    for country, config in COUNTRY_CONFIG.items():

        filename = config["redemption_file"]
        file_path = Path(data_dir) / filename

        if not file_path.exists():
            print(
                f"\nRedemption file not found for {country}: "
                f"{filename}. Skipping."
            )
            continue

        print(f"\nReading redemption file: {filename}")

        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            records = [data]

        elif isinstance(data, list):
            records = data

        else:
            raise ValueError(
                f"Invalid JSON structure in {filename}"
            )

        for record in records:

            if not isinstance(record, dict):
                raise ValueError(
                    f"Invalid record in {filename}: "
                    "Expected a JSON object."
                )

            record = record.copy()
            record["country_code"] = country

            all_redemptions.append(record)

        print(
            f"Loaded {len(records)} redemption record(s) "
            f"for {country}."
        )

    if not all_redemptions:
        print(
            "\nNo redemption JSON files found. "
            "Skipping redemption ingestion."
        )
        return None

    print(
        f"\nTotal redemption feed records ingested: "
        f"{len(all_redemptions)}"
    )

    return all_redemptions
