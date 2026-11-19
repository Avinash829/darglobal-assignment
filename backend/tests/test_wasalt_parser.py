"""The Wasalt sitemap URL parser turns URLs into structured fields."""

from scraper.wasalt import parse_category, parse_daily_rental, parse_listing


def test_parse_listing_with_size_and_street():
    listing = parse_listing("https://wasalt.sa/en/property/sale/villa-333-sqm-facing-east-on-20m-width-street-5841671")
    assert listing["id"] == "5841671"
    assert listing["purpose"] == "sale"
    assert listing["property_type"] == "villa"
    assert listing["area_sqm"] == 333
    assert listing["facing"] == "east"
    assert listing["street_width_m"] == 20


def test_parse_listing_with_bedrooms():
    listing = parse_listing("https://wasalt.sa/en/property/rent/apartment-100-sqm-with-1-bedroom-5856684")
    assert listing["property_type"] == "apartment"
    assert listing["bedrooms"] == 1
    assert listing["area_sqm"] == 100


def test_unbelievable_area_is_dropped():
    # "54387 sqm" for an apartment is a missing decimal point in the URL.
    listing = parse_listing("https://wasalt.sa/en/property/sale/apartment-54387-sqm-with-3-bedrooms-5875340")
    assert listing["area_sqm"] is None


def test_parse_daily_rental():
    rental = parse_daily_rental("https://wasalt.sa/en/dailyrental/chalet-for-booking-5582")
    assert rental["purpose"] == "daily rental"
    assert rental["property_type"] == "chalet"


def test_parse_category_with_location_and_price_band():
    category = parse_category("https://wasalt.sa/en/villas-for-sale-in-central-riyadh-umm-saleem")
    assert category["category"] == "villas"
    assert category["location"] == "Central Riyadh Umm Saleem"
    priced = parse_category("https://wasalt.sa/en/properties-for-sale-in-jeddah-for-sar-5000k")
    assert priced["location"] == "Jeddah"
    assert priced["max_price"] == "SAR 5000K"
