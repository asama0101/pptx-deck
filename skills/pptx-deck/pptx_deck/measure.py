"""final.html を Playwright(Python) で開き、部品の位置・大きさ・書式をモデルにする。"""
from pathlib import Path


def measure(html: Path) -> list[dict]:
    from playwright.sync_api import sync_playwright

    js = (Path(__file__).parent / "measure.js").read_text(encoding="utf-8")
    html = Path(html).resolve()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            page.goto(html.as_uri())
            page.evaluate("document.fonts.ready.then(() => true)")
            slides = page.evaluate(js)
        finally:
            browser.close()
    if not slides:
        raise ValueError(f"{html.name} に section.slide がありません")
    return slides


def title_of(slide: dict) -> dict | None:
    for e in slide["elements"]:
        if e["kind"] == "text" and (e.get("role") == "title" or e.get("ph") == "title"):
            return e
    return None
