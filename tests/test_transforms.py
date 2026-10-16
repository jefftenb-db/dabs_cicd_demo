import pytest

from dabs_cicd_demo.transforms import revenue_by_destination


@pytest.fixture()
def result(load_fixture):
    return revenue_by_destination(
        load_fixture("bookings.json"),
        load_fixture("properties.json"),
        load_fixture("destinations.json"),
    )


def test_output_columns(result):
    assert result.columns == ["destination", "country", "total_revenue", "booking_count"]


def test_only_completed_bookings_are_counted(result):
    rows = {r.destination: r for r in result.collect()}
    # Kyoto has one completed (500) and one cancelled (900) booking.
    assert rows["Kyoto"].total_revenue == 500.0
    assert rows["Kyoto"].booking_count == 1
    # Lisbon's pending booking (75) is excluded.
    assert rows["Lisbon"].total_revenue == 350.0
    assert rows["Lisbon"].booking_count == 2


def test_bookings_without_matching_property_are_dropped(result):
    # booking 6 references a property that does not exist.
    assert result.count() == 2
    assert sum(r.booking_count for r in result.collect()) == 3


def test_sorted_by_revenue_descending(result):
    revenues = [r.total_revenue for r in result.collect()]
    assert revenues == sorted(revenues, reverse=True)
    assert result.first().destination == "Kyoto"


def test_country_is_carried_through(result):
    assert {(r.destination, r.country) for r in result.collect()} == {("Lisbon", "Portugal"), ("Kyoto", "Japan")}
