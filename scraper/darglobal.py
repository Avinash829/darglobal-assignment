"""
Scrape public project and company pages from darglobal.co.uk.

How it works:
1. Open /projects and read the Next.js page data (__NEXT_DATA__) to get every
   project card: title, location, type, bedrooms, completion date, link.
2. Visit each project page and each company page and keep the readable text.
3. Save everything to data/raw/darglobal_pages.json.

Run:  python -m scraper.darglobal
"""

import json
from playwright.sync_api import Page, sync_playwright

from scraper.common import USER_AGENT, polite_pause, save_json

BASE_URL = "https://darglobal.co.uk"

# Company pages that describe DarGlobal itself (found in the site navigation).
COMPANY_PAGE_PATHS = [
    "/", "/about", "/faq", "/luxury-golf-communities", "/hospitality",
    "/commercial", "/tokenization", "/investor", "/get-in-touch",
    "/partners/the-trump-organization", "/partners/lamborghini", "/partners/pagani",
    "/partners/fendi-casa", "/partners/aston-martin", "/partners/w-hotels",
    "/partners/missoni", "/partners/elie-saab", "/partners/paramount",
]

# The page text after these markers is the enquiry form / cookie banner.
TEXT_END_MARKERS = ["REGISTER YOUR INTEREST", "We value our privacy"]
PAGE_LOAD_WAIT_MS = 5000


def open_page(page: Page, url: str) -> None:
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(PAGE_LOAD_WAIT_MS)  # let the JS finish rendering


def read_project_cards(page: Page) -> list[dict]:
    """Return one dict per project from the /projects page data."""
    open_page(page, f"{BASE_URL}/projects")
    next_data = json.loads(page.evaluate("() => document.getElementById('__NEXT_DATA__').textContent"))
    country_tabs = next_data["props"]["pageProps"]["pageData"]["attributes"]["Tabs"]

    projects_by_link = {}
    for tab in country_tabs:
        for card in tab["TabData"]:
            projects_by_link[card["Link"]] = {
                "title": card["ProjectTitle"],
                "country": tab["TabHeading"],
                "location": card["Location"],
                "property_type": card["ProjectType"],
                "bedrooms": card["Bedrooms"],
                "completion_date": card["completionDate"],
                "url": BASE_URL + card["Link"],
            }
    return list(projects_by_link.values())


def read_page_text(page: Page, url: str) -> tuple[str, str]:
    """Return (title, cleaned visible text) of a page."""
    open_page(page, url)
    text = page.inner_text("body")

    # Start at the main heading, skipping the top navigation bar.
    main_heading = page.eval_on_selector("h1", "el => el.innerText") if page.query_selector("h1") else ""
    title = page.title() or main_heading.title() or url
    if main_heading and main_heading in text:
        text = text[text.index(main_heading):]

    # Stop before the enquiry form and cookie banner.
    for marker in TEXT_END_MARKERS:
        if marker in text:
            text = text[: text.index(marker)]

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return title, "\n".join(lines)


def scrape_darglobal() -> list[dict]:
    pages = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(user_agent=USER_AGENT)

        projects = read_project_cards(page)
        print(f"Found {len(projects)} projects")

        for index, project in enumerate(projects, start=1):
            polite_pause()
            try:
                _, project["text"] = read_page_text(page, project["url"])
                project["page_type"] = "project"
                pages.append(project)
                print(f"[{index}/{len(projects)}] {project['title']}")
            except Exception as error:  # keep going if one page fails
                print(f"  skipped {project['url']}: {error}")

        for path in COMPANY_PAGE_PATHS:
            polite_pause()
            url = BASE_URL + path
            try:
                title, text = read_page_text(page, url)
                pages.append({"title": title, "url": url, "page_type": "company", "text": text})
                print(f"[company] {title}")
            except Exception as error:
                print(f"  skipped {url}: {error}")

        browser.close()
    return pages


if __name__ == "__main__":
    save_json(scrape_darglobal(), "darglobal_pages.json")
