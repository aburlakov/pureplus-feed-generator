"""
batch_render.py — Sequential rendering на много продукти
─────────────────────────────────────────────────────────────
Пуска ЕДИН Chromium browser с ЕДНА page и рендерира всички
продукти секвенциално.

Защо не concurrent: Playwright sync API НЕ е thread-safe.
За ~100 продукта секвенциалното рендериране отнема ~3-4 мин,
което е напълно достатъчно за дневен job. Простота > сложност.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
from src.render import render_one

OUT_DIR = "docs/images"


def render_batch(products, out_dir=OUT_DIR):
    """
    Рендерира списък от продукти един по един.
    Връща (succeeded, failed) списъци.
    """
    if not products:
        print("✅ Нищо за рендериране — всичко е up to date.")
        return [], []

    print(f"🎨 Рендерирам {len(products)} продукта...")

    succeeded = []
    failed = []

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(
            viewport={"width": 1080, "height": 1080},
            device_scale_factor=2,
        )

        for i, product in enumerate(products, 1):
            pid = product["id"]
            try:
                render_one(product, page, out_dir)
                succeeded.append(pid)
                print(f"  [{i}/{len(products)}] ✓ {pid}")
            except Exception as e:
                failed.append((pid, str(e)))
                print(f"  [{i}/{len(products)}] ✗ {pid} — ГРЕШКА: {str(e)[:80]}")

        browser.close()

    print(f"\n📊 Готово: {len(succeeded)} успешни, {len(failed)} неуспешни")
    return succeeded, failed