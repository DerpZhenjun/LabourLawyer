"""Render our original SVGs to local PNGs for WeChat's image component."""
import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
async def main():
    temp=ROOT/'.runtime/temp';temp.mkdir(parents=True,exist_ok=True);os.environ.update(TEMP=str(temp),TMP=str(temp))
    output=ROOT/'miniprogram/assets/province-art';output.mkdir(parents=True,exist_ok=True)
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,chromium_sandbox=True)
        page=await browser.new_page(viewport={'width':380,'height':260},device_scale_factor=1)
        for source in (ROOT/'frontend/public/province-art').glob('*.svg'):
            await page.set_content('<style>body{margin:0}</style>'+source.read_text(encoding='utf8'))
            await page.screenshot(path=str(output/(source.stem+'.png')),omit_background=True)
        await browser.close()
    print('Rendered 31 WeChat province illustrations')
asyncio.run(main())
