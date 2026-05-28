"""
settings.py — централизирана конфигурация
─────────────────────────────────────────────────────────────
Всички URL-и, пътища и константи на едно място.
Когато се промени URL, променяме само тук, не из целия код.
"""

# ── Източник на данни ─────────────────────────────────────
SOURCE_FEED_URL = "https://pureplus.bg/wp-content/uploads/woo-product-feed-pro/xml/7i614t6chm0ipgkamljtn5sutl0h84ym.xml"

# ── GitHub Pages (твоят hosting) ──────────────────────────
GITHUB_USER = "aburlakov"
GITHUB_REPO = "pureplus-feed-generator"
PAGES_BASE_URL = f"https://{GITHUB_USER}.github.io/{GITHUB_REPO}"

# Public URL към генерираните изображения
IMAGES_BASE_URL = f"{PAGES_BASE_URL}/images"

# Public URL към генерирания feed (даваме го на Meta)
FEED_URL = f"{PAGES_BASE_URL}/feed.xml"

# ── Локални пътища ────────────────────────────────────────
OUTPUT_DIR = "docs"           # GitHub Pages serve-ва оттук
IMAGES_DIR = "docs/images"
FEED_OUTPUT = "docs/feed.xml"