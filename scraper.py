from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

ENTERTAINMENT_URL = "https://ekantipur.com/entertainment"
CARTOON_URL = "https://ekantipur.com/cartoon"
SITE_ORIGIN = "https://ekantipur.com"
OUTPUT_PATH = Path(__file__).resolve().parent / "output.json"


def absolute_url(href: str | None) -> str | None:
    """Turn relative or protocol-relative URLs into ekantipur.com URLs."""
    if not href:
        return None
    raw = href.strip()
    if not raw:
        return None
    if raw.startswith("https://"):
        return raw
    if raw.startswith("http://"):
        return "https://" + raw.removeprefix("http://")
    if raw.startswith("//"):
        return "https:" + raw
    if raw.startswith("/"):
        return SITE_ORIGIN + raw
    return f"{SITE_ORIGIN}/{raw.lstrip('/')}"


def extract_entertainment_articles(page: Page) -> list[dict]:
    """Collect up to five listing cards from the entertainment section."""
    cards = page.query_selector_all("div.category")[:5]
    entertainment_news: list[dict] = []

    section_heading = page.query_selector("h1.section-title, h1, .category-title, header h1")
    category_name = section_heading.text_content().strip() if section_heading else "मनोरञ्जन"

    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(1500)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(500)

    for index, card in enumerate(cards):
        try:
            title_el = card.query_selector("h2 a")
            if not title_el:
                print(f"Card {index}: skipping — no h2 a found", file=sys.stderr)
                continue

            title = (title_el.text_content() or "").strip()
            url = absolute_url(title_el.get_attribute("href"))

            author_el = card.query_selector("div.author-name p a")
            author = (author_el.text_content() or "").strip() or None if author_el else None

            img_el = card.query_selector("div.category-image a figure img")
            image_url = (
                absolute_url(img_el.get_attribute("src") or img_el.get_attribute("data-src"))
                if img_el else None
            )

            entertainment_news.append({
                "title": title,
                "url": url,
                "author": author,
                "image_url": image_url,
                "category": category_name,
            })
            print(title)
        except Exception as exc:
            print(f"Card {index} extraction failed: {exc}", file=sys.stderr)

    return entertainment_news


def extract_cartoon_of_the_day(page: Page) -> dict:
    """Load the cartoon page and parse today's cartoon."""
    null_cartoon = {"title": None, "image_url": None, "author": None}

    try:
        page.goto(CARTOON_URL, wait_until="load")
        try:
            page.wait_for_load_state("networkidle")
        except PlaywrightTimeoutError as exc:
            print(
                f"Cartoon page networkidle timed out (continuing): {exc}",
                file=sys.stderr,
            )

        page.evaluate("window.scrollTo(0, 500)")
        page.wait_for_timeout(1000)

        container = page.query_selector("div.cartoon-wrapper")
        if not container:
            return null_cartoon

        img_el = container.query_selector("div.cartoon-image figure img")
        image_url = img_el.get_attribute("src") if img_el else None

        desc_el = container.query_selector("div.cartoon-description p")
        if desc_el:
            raw_text = (desc_el.text_content() or "").strip()

            if " - " in raw_text:
                parts = raw_text.split(" - ", 1)
                title = parts[0].strip()
                author = parts[1].strip() if parts[1].strip() else None
            elif raw_text.endswith(" -") or raw_text.endswith("-"):
                title = raw_text.rstrip("-").strip()
                author = None
            else:
                title = raw_text
                author = None
        else:
            title = None
            author = None

        return {"title": title, "image_url": image_url, "author": author}
    except Exception as exc:
        print(f"Cartoon extraction failed: {exc}", file=sys.stderr)
        return null_cartoon


def main() -> None:
    """Orchestrate browser launch, navigation, extraction, and JSON export."""

    result: dict = {
        "entertainment_news": [],
        "cartoon_of_the_day": None,
    }

    try:
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True)
            except Exception as exc:
                print(f"Could not launch Chromium: {exc}", file=sys.stderr)
                return

            try:
                page = browser.new_page()

                try:
                    page.goto(ENTERTAINMENT_URL, wait_until="load")
                except PlaywrightTimeoutError as exc:
                    print(f"Timed out loading the page (goto): {exc}", file=sys.stderr)
                    return
                except Exception as exc:
                    print(f"Navigation error: {exc}", file=sys.stderr)
                    return

                try:
                    page.wait_for_load_state("networkidle")
                except PlaywrightTimeoutError as exc:
                    print(
                        f"networkidle wait timed out (site may keep connections open): {exc}",
                        file=sys.stderr,
                    )

                result["entertainment_news"] = extract_entertainment_articles(page)
                result["cartoon_of_the_day"] = extract_cartoon_of_the_day(page)

            except Exception as exc:
                print(f"Unexpected error during scraping: {exc}", file=sys.stderr)
            finally:
                try:
                    browser.close()
                except Exception as exc:
                    print(f"Error while closing the browser: {exc}", file=sys.stderr)

    except Exception as exc:
        print(f"Playwright session failed: {exc}", file=sys.stderr)

    try:
        OUTPUT_PATH.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"Could not write {OUTPUT_PATH}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
