# ekantipur-scraper

Sync Playwright script that pulls the first five entertainment listing cards from [ekantipur.com/entertainment](https://ekantipur.com/entertainment) and the first cartoon card from [ekantipur.com/cartoon](https://ekantipur.com/cartoon), then writes `output.json`.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (dependency install and `uv run`)

## Setup

1. `uv init` — not needed if you already have this repo; it only applies to a brand-new directory.
2. `uv add playwright` — skip if `pyproject.toml` already includes Playwright; otherwise `uv sync` from the lockfile is enough.
3. `uv run playwright install chromium`

## Run

```bash
uv run python scraper.py
```

Chromium is configured in `scraper.py` (currently headless). JSON is written next to the script as `output.json`.

## Output structure

Shape only (no real article text); optional fields may be `null` in practice.

```json
{
  "entertainment_news": [
    {
      "title": "string",
      "url": "string | null",
      "author": "string | null",
      "image_url": "string | null",
      "category": "string"
    }
  ],
  "cartoon_of_the_day": {
    "title": "string | null",
    "image_url": "string | null",
    "author": "string | null"
  }
}
```

`entertainment_news` has at most five items. `cartoon_of_the_day` is always an object after a full run; if extraction fails, that object has all three keys set to `null`. If the script exits very early (e.g. before the cartoon step), `cartoon_of_the_day` may stay `null` in the written file.

## Notes

- Listing and cartoon pages are scrolled briefly before reading images so lazy-loaded `src` / `data-src` values have a chance to populate.
- JSON is written with `ensure_ascii=False` so Nepali / Devanagari text is stored as Unicode in the file, not `\u` escapes.
- Selectors follow the current ekantipur layout; if the site changes markup, this script will need updates.
