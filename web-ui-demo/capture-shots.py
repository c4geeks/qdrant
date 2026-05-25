#!/usr/bin/env python3
"""Capture every Qdrant Web UI panel as a 1440x900 PNG.

Companion to: https://computingforgeeks.com/qdrant-web-ui-guide/

The Web UI is a React SPA. Some panels (Visualize, Graph) only render their
plot after a RUN button is clicked, so headless Chrome alone is not enough.
This script uses Playwright to click and wait. See the article's "Gotchas
worth knowing" section for why each wait time was chosen.

Usage:
    python3 -m venv venv && source venv/bin/activate
    pip install playwright
    playwright install chromium
    python3 capture-shots.py             # writes ./shots/*.png
    python3 capture-shots.py --host http://10.0.1.50:6333 --collection midlib
"""
from __future__ import annotations
import argparse, asyncio, os
from playwright.async_api import async_playwright

OUT = "shots"


async def click_run(page) -> None:
    try:
        await page.get_by_text("RUN", exact=True).first.click(timeout=8000)
    except Exception as exc:
        print(f"    (RUN click failed: {exc})")


async def shoot(page, name: str, url: str, wait_ms: int = 3500, run: bool = False) -> None:
    print(f"==> {name}: {url}")
    await page.goto(url, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(wait_ms)
    if run:
        await click_run(page)
        await page.wait_for_timeout(8000)
    path = f"{OUT}/{name}.png"
    await page.screenshot(path=path, full_page=False)
    print(f"    -> {path} ({os.path.getsize(path)} bytes)")


async def main(host: str, collection: str) -> None:
    os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()

        await shoot(page, "01-collections",         f"{host}/dashboard#/")
        await shoot(page, "02-welcome",             f"{host}/dashboard#/welcome", 4000)
        await shoot(page, "03-console",             f"{host}/dashboard#/console", 4500)
        await shoot(page, "04-datasets",            f"{host}/dashboard#/datasets", 4500)
        await shoot(page, "05-collection-detail",   f"{host}/dashboard#/collections/{collection}", 4500)
        await shoot(page, "06-visualize",           f"{host}/dashboard#/collections/{collection}/visualize", 4500, run=True)
        await shoot(page, "07-graph",               f"{host}/dashboard#/collections/{collection}/graph", 4500, run=True)
        await shoot(page, "08-tutorial-index",      f"{host}/dashboard#/tutorial", 4000)
        await shoot(page, "09-tutorial-filtering",  f"{host}/dashboard#/tutorial/filteringbeginner", 4500)
        await shoot(page, "10-access-tokens",       f"{host}/dashboard#/jwt", 6000)

        await browser.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://localhost:6333")
    ap.add_argument("--collection", default="midlib",
                    help="Collection name used for the Visualize / Graph / detail screenshots")
    args = ap.parse_args()
    asyncio.run(main(args.host, args.collection))
