"""Pure DataFrame transformations. Kept free of I/O so they can be unit tested with local Spark."""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def revenue_by_destination(bookings: DataFrame, properties: DataFrame, destinations: DataFrame) -> DataFrame:
    """Total revenue and booking count of completed bookings per destination, highest revenue first."""
    return (
        bookings.filter(F.col("status") == "completed")
        .join(properties, "property_id")
        .join(destinations, "destination_id")
        .groupBy("destination", "country")
        .agg(
            F.sum("total_amount").alias("total_revenue"), 
            F.count("booking_id").alias("booking_count")
        )
        .orderBy(F.desc("total_revenue"))
    )
