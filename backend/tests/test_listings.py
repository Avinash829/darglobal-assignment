"""Exact listing filters: reading filters from a question and applying them."""

from app.listings import ListingFilters, find_listings, matches, parse_filters


def test_reads_purpose_type_and_bedrooms():
    filters = parse_filters("Show me 3 bedroom apartments for rent")
    assert filters.purpose == "rent"
    assert filters.property_type == "apartment"
    assert filters.bedrooms == 3


def test_reads_area_limits():
    filters = parse_filters("land for sale over 500 sqm")
    assert filters.purpose == "sale"
    assert filters.property_type == "land"
    assert filters.min_area_sqm == 500


def test_daily_rental_and_synonyms():
    assert parse_filters("chalet for daily booking").purpose == "daily rental"
    assert parse_filters("2 bhk flat to buy").property_type == "apartment"


def test_question_without_filters_is_empty():
    assert parse_filters("Tell me about Trump Tower Jeddah").is_empty()


def test_matches_checks_every_filter():
    listing = {"purpose": "rent", "property_type": "apartment", "bedrooms": 3, "area_sqm": 150}
    assert matches(listing, ListingFilters(purpose="rent", bedrooms=3, max_area_sqm=200))
    assert not matches(listing, ListingFilters(purpose="sale"))
    assert not matches(listing, ListingFilters(min_area_sqm=200))


def test_find_listings_returns_only_matching_examples():
    filters = ListingFilters(purpose="sale", property_type="villa")
    total, examples = find_listings(filters)
    assert total > 1000
    assert examples and all(item["purpose"] == "sale" and "villa" in item["property_type"] for item in examples)
