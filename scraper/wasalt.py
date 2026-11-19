"""
Collect public Wasalt data from the sitemaps it publishes in robots.txt.

Why sitemaps: Wasalt's listing pages are protected by a Cloudflare bot check,
which we respect and do not try to bypass. Its sitemaps are published for
crawlers, and the listing URLs describe each property, for example:

    /en/property/sale/villa-333-sqm-facing-east-on-20m-width-street-5841671
    /en/villas-for-sale-in-central-riyadh-umm-saleem

We parse those URLs into structured fields. No contact details are collected,
in line with https://wasalt.sa/llms.txt.

Run:  python -m scraper.wasalt
"""

import gzip
import re
import urllib.request

from scraper.common import USER_AGENT, polite_pause, save_json

SITEMAP_BASE_URL = "https://cdn.wasalt.sa/sitemap"
LISTINGS_SITEMAP = "product_sitemap_en_sa"        # properties for sale and rent
DAILY_RENTALS_SITEMAP = "rental_pdp_sitemap_en_sa"  # chalets, apartments for booking
CATEGORY_SITEMAPS = ["category_sitemap_en_sa", "rental_srp_sitemap_en_sa"]  # by city/district

# Sizes above this are almost always a missing decimal point in the URL
# (e.g. "54387-sqm" for a 543.87 sqm apartment), so we drop them.
MAX_BELIEVABLE_AREA_SQM = 5000


def download_sitemap(name: str) -> list[dict]:
    """Return [{"url": ..., "last_modified": ...}] for every entry in a sitemap."""
    request = urllib.request.Request(f"{SITEMAP_BASE_URL}/{name}.xml.gz", headers={"User-Agent": USER_AGENT})
    content = urllib.request.urlopen(request, timeout=60).read()
    if content[:2] == b"\x1f\x8b":  # some files are gzipped, some are not
        content = gzip.decompress(content)
    xml = content.decode("utf-8")
    entries = re.findall(r"<loc>(.*?)</loc>\s*(?:<lastmod>(.*?)</lastmod>)?", xml)
    print(f"{name}: {len(entries)} URLs")
    return [{"url": url, "last_modified": last_modified or None} for url, last_modified in entries]


def find_number(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text)
    return int(match.group(1)) if match else None


def parse_listing(url: str) -> dict:
    """Turn a listing URL into structured fields."""
    # e.g. .../property/sale/apartment-120-sqm-with-3-bedrooms-5841667
    _, purpose, slug = url.rsplit("/", 2)
    listing_id = slug.rsplit("-", 1)[-1]
    description = slug.rsplit("-", 1)[0]

    property_type = re.split(r"-(?=\d|with-|facing-|for-)", description)[0].replace("-", " ")
    area_sqm = find_number(r"(\d+)-sqm", description)
    if area_sqm and area_sqm > MAX_BELIEVABLE_AREA_SQM and property_type not in ("land", "building"):
        area_sqm = None
    facing = re.search(r"facing-(.+?)(?:-on-|$)", description)

    return {
        "id": listing_id,
        "purpose": purpose,                      # "sale" or "rent"
        "property_type": property_type,          # "apartment", "villa", "land", ...
        "bedrooms": find_number(r"with-(\d+)-bedroom", description),
        "area_sqm": area_sqm,
        "facing": facing.group(1).replace("-", " ") if facing else None,
        "street_width_m": find_number(r"on-(\d+)m-width", description),
        "title": description.replace("-", " ").capitalize(),
        "url": url,
    }


def parse_daily_rental(url: str) -> dict:
    # e.g. .../dailyrental/chalet-for-booking-5582
    slug = url.rsplit("/", 1)[-1]
    return {
        "id": "daily-" + slug.rsplit("-", 1)[-1],
        "purpose": "daily rental",
        "property_type": slug.split("-for-")[0].replace("-", " "),
        "bedrooms": None, "area_sqm": None, "facing": None, "street_width_m": None,
        "title": slug.rsplit("-", 1)[0].replace("-", " ").capitalize(),
        "url": url,
    }


def parse_category(url: str) -> dict | None:
    """
    '/en/villas-for-sale-in-central-riyadh-umm-saleem'  -> category, purpose, location
    '/en/properties-for-sale-in-jeddah-for-sar-5000k'   -> ... plus max_price "SAR 5000K"
    """
    slug = url.rsplit("/", 1)[-1]
    match = re.match(r"(.+?)-for-(sale|rent|daily-rental)-in-(.+?)(?:-for-sar-(\w+))?$", slug)
    if not match:
        return None
    category, purpose, location, max_price = match.groups()
    return {
        "category": category.replace("-", " "),
        "purpose": purpose.replace("-", " "),
        "location": location.replace("-", " ").title(),
        "max_price": f"SAR {max_price.upper()}" if max_price else None,
        "url": url,
    }


def scrape_wasalt() -> tuple[list[dict], list[dict]]:
    listings = []
    for entry in download_sitemap(LISTINGS_SITEMAP):
        listing = parse_listing(entry["url"])
        listing["last_modified"] = entry["last_modified"]
        listings.append(listing)
    polite_pause()

    for entry in download_sitemap(DAILY_RENTALS_SITEMAP):
        listing = parse_daily_rental(entry["url"])
        listing["last_modified"] = entry["last_modified"]
        listings.append(listing)

    categories = []
    for sitemap_name in CATEGORY_SITEMAPS:
        polite_pause()
        for entry in download_sitemap(sitemap_name):
            category = parse_category(entry["url"])
            if category:
                categories.append(category)

    return listings, categories


if __name__ == "__main__":
    all_listings, all_categories = scrape_wasalt()
    save_json(all_listings, "wasalt_listings.json")
    save_json(all_categories, "wasalt_categories.json")
