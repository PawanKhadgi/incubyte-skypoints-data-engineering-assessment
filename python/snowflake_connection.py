
import os
import snowflake.connector
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv()


def get_snowflake_connection():

    connection = snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE")
    )

    return connection


def test_connection():

    connection = None

    try:
        connection = get_snowflake_connection()

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                CURRENT_DATABASE(),
                CURRENT_SCHEMA(),
                CURRENT_WAREHOUSE(),
                CURRENT_ROLE()
        """)

        result = cursor.fetchone()

        print("Snowflake connection successful!")
        print(f"Database: {result[0]}")
        print(f"Schema: {result[1]}")
        print(f"Warehouse: {result[2]}")
        print(f"Role: {result[3]}")

        cursor.close()

    except Exception as error:
        print("Snowflake connection failed!")
        print(f"Error: {error}")

    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    test_connection()
