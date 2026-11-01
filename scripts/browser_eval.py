#!/usr/bin/env python3
"""Offline artifact checks. Uses an already installed Playwright; never installs it."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from playwright.async_api import async_playwright

CHROMIUM = None  # Use the explicit existing executable, or Playwright’s existing cached executable.

async def run(args):
    source = Path(args.input).resolve()
    target = Path(args.output).resolve()
    target.mkdir(parents=True, exist_ok=True)
    report = {"input": str(source), "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "recorded_at": datetime.now(timezone.utc).isoformat(), "checks": [], "external_requests": [], "page_errors": [], "scope": "Offline browser artifact functionality only; no audience or model quality measurement."}
    def check(name, passed, **detail):
        report["checks"].append({"name": name, "passed": bool(passed), **detail})
        (target / "RESULT.partial.json").write_text(json.dumps(report, indent=2) + "\n")
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=args.chromium or CHROMIUM, headless=True, args=["--disable-background-networking"])
        context = await browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        async def route(request):
            report["external_requests"].append(request.request.url)
            await request.abort()
        await context.route("**/*", route)
        page = await context.new_page()
        page.on("pageerror", lambda error: report["page_errors"].append(str(error)))
        await page.set_content(source.read_text(), wait_until="load")
        count = await page.locator("section.slide").count()
        check("nine readable source slides", count == 9, actual=count)
        check("initial slide", await page.locator("#opening").evaluate("e=>e.classList.contains('active')"))
        await page.keyboard.press("ArrowRight")
        check("keyboard next", await page.locator("#human-moment").evaluate("e=>e.classList.contains('active')"))
        await page.locator("#notes-button").click()
        check("notes open", await page.locator("#notes-panel").evaluate("e=>e.classList.contains('open')"))
        await page.keyboard.press("Escape")
        await page.locator("#overview-button").click()
        check("overview contains every slide", await page.locator("#overview-grid button").count() == count)
        await page.locator("#overview-grid button").first.click()
        await page.locator("#edit-button").click()
        title = page.locator('[data-edit="title"]')
        await title.fill("The first question matters — fictional draft")
        await title.press("ArrowRight")
        check("navigation does not intercept author typing", await page.locator("#opening").evaluate("e=>e.classList.contains('active')"))
        try:
            async with page.expect_download(timeout=2500) as download_info:
                await page.locator("#download").click()
            download = await download_info.value
            dest = target / "exported-talk.html"
            await download.save_as(dest)
            exported = dest.read_text()
            check("HTML export succeeds", True)
            check("export contains edited words", "The first question matters — fictional draft" in exported)
            exported_page = await context.new_page()
            await exported_page.set_content(exported, wait_until="load")
            check("export reopens with all slides", await exported_page.locator("section.slide").count() == count)
            check("export has fresh draft identity", await exported_page.locator("body").get_attribute("data-deck-id") != await page.locator("body").get_attribute("data-deck-id"))
            check("export resets editing", await exported_page.locator("#edit-button").get_attribute("aria-pressed") == "false")
            await exported_page.close()
        except Exception as error:
            check("HTML export succeeds", False, error=str(error))
        try:
            await page.locator("#edit-button").click(timeout=2500)
            check("Finish editing remains accessible", True)
        except Exception as error:
            check("Finish editing remains accessible", False, error=str(error))
            # Retain the failure; reset only to independently exercise remaining cases.
            await page.set_content(source.read_text(), wait_until="load")
        for width in [1440, 390, 360]:
            await page.set_viewport_size({"width": width, "height": 1000})
            overflows = []
            for i in range(count):
                await page.keyboard.press("Home")
                for _ in range(i):
                    await page.keyboard.press("ArrowRight")
                overflow = await page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
                if overflow:
                    overflows.append(i + 1)
            check(f"no document overflow at {width}px", not overflows, slides=overflows)
            if width == 390:
                await page.keyboard.press("Home")
                await page.screenshot(path=str(target / "phone.png"), full_page=True)
        await page.set_viewport_size({"width": 1440, "height": 1000})
        await page.keyboard.press("Home")
        await page.screenshot(path=str(target / "desktop.png"), full_page=True)
        await page.emulate_media(media="print")
        visible_print = await page.locator("section.slide").evaluate_all("els=>els.filter(e=>getComputedStyle(e).display!=='none').length")
        check("print media shows every slide", visible_print == count, actual=visible_print)
        await page.pdf(path=str(target / "talk-print.pdf"), landscape=True, print_background=True)
        check("print PDF generated", (target / "talk-print.pdf").stat().st_size > 0)
        nojs = await browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 1000})
        await nojs.route("**/*", lambda route: route.abort())
        reading = await nojs.new_page()
        await reading.set_content(source.read_text(), wait_until="load")
        visible_read = await reading.locator("section.slide").evaluate_all("els=>els.filter(e=>getComputedStyle(e).display!=='none').length")
        check("no-JavaScript mode shows every slide", visible_read == count, actual=visible_read)
        check("no external requests", len(report["external_requests"]) == 0)
        check("no browser JavaScript errors", len(report["page_errors"]) == 0, errors=report["page_errors"])
        await browser.close()
    report["passed"] = all(x["passed"] for x in report["checks"])
    report["passed_checks"] = sum(x["passed"] for x in report["checks"])
    report["total_checks"] = len(report["checks"])
    (target / "RESULT.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ["passed", "passed_checks", "total_checks", "page_errors"]}))
    return 0 if report["passed"] else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--chromium", help="Existing Chromium executable; no download is attempted")
    raise SystemExit(asyncio.run(run(parser.parse_args())))
