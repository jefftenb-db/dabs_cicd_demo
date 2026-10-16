import argparse

from pyspark.sql import SparkSession

from dabs_cicd_demo.transforms import revenue_by_destination


def main():
    # Process command-line arguments
    parser = argparse.ArgumentParser(
        description="Databricks job with catalog and schema parameters",
    )
    parser.add_argument("--catalog_source", required=True)
    parser.add_argument("--catalog_target", required=True)
    parser.add_argument("--schema_target", required=True)
    args = parser.parse_args()

    spark = SparkSession.builder.getOrCreate()

    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {args.catalog_target}.{args.schema_target}")

    bookings = spark.table(f"{args.catalog_source}.wanderbricks.bookings")
    properties = spark.table(f"{args.catalog_source}.wanderbricks.properties")
    destinations = spark.table(f"{args.catalog_source}.wanderbricks.destinations")

    revenue_by_destination(bookings, properties, destinations).write.mode("overwrite").saveAsTable(
        f"{args.catalog_target}.{args.schema_target}.revenue_by_destination"
    )


if __name__ == "__main__":
    main()
