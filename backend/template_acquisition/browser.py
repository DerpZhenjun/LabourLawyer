from __future__ import annotations

import os
from pathlib import Path

from playwright.async_api import async_playwright
from tenacity import retry, stop_after_attempt, wait_exponential


CHROME_PATHS = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
)


def find_chrome() -> Path:
    for path in CHROME_PATHS:
        if path.exists():
            return path
    raise FileNotFoundError("Google Chrome was not found; configure a system Chrome installation")


@retry(wait=wait_exponential(multiplier=1, min=2, max=8), stop=stop_after_attempt(3), reraise=True)
async def capture_guide(url: str, output: Path, focus_terms: tuple[str, ...] = ()) -> tuple[Path, Path]:
    output.mkdir(parents=True, exist_ok=True)
    screenshot = output / "guide.png"
    page_text = output / "guide.txt"
    browser_profile = output / "browser-profile"
    browser_profile.mkdir(parents=True, exist_ok=True)
    process_temp = output / "browser-temp"
    process_temp.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser_env = os.environ.copy()
        browser_env.update({"TEMP": str(process_temp.resolve()), "TMP": str(process_temp.resolve())})
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(browser_profile.resolve()),
            headless=True,
            chromium_sandbox=True,
            executable_path=str(find_chrome()),
            args=["--disable-gpu"],
            locale="zh-CN",
            viewport={"width": 1440, "height": 1000},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
            ),
            env=browser_env,
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=90_000)
        await page.wait_for_timeout(8_000)
        focused = False
        for term in focus_terms:
            locator = page.get_by_text(term, exact=False)
            for index in range(min(await locator.count(), 20)):
                item = locator.nth(index)
                if not await item.is_visible():
                    continue
                try:
                    await item.scroll_into_view_if_needed(timeout=5_000)
                    await page.wait_for_timeout(1_000)
                    focused = True
                except Exception:
                    pass
                break
            if focused:
                break
        await page.screenshot(path=screenshot, full_page=False)
        page_text.write_text(await page.locator("body").inner_text(), encoding="utf-8")
        await context.close()
    return screenshot, page_text
