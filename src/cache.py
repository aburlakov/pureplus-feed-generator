"""
cache.py — Change detection
─────────────────────────────────────────────────────────────
Хешира всеки продукт по полетата, които влияят на визията.
Ако хешът съвпада с предишния — прескачаме рендерирането.
"""
import json
import hashlib
from pathlib import Path

CACHE_FILE = Path("cache/products_hash.json")


def _product_hash(product):
    relevant = "|".join([
        str(product.get("title", "")),
        str(product.get("image_link", "")),
        str(product.get("price_value", "")),
        str(product.get("sale_price_value", "")),
        str(product.get("discount_percent", "")),
        str(product.get("product_type", "")),
    ])
    return hashlib.md5(relevant.encode("utf-8")).hexdigest()


def load_cache():
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def save_cache(hashes):
    CACHE_FILE.parent.mkdir(exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps(hashes, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def split_products(products, images_dir="docs/images"):
    old_hashes = load_cache()
    images_dir = Path(images_dir)
    to_render, unchanged, new_hashes = [], [], {}

    for p in products:
        pid = p["id"]
        h = _product_hash(p)
        new_hashes[pid] = h
        image_exists = (images_dir / f"{pid}.jpg").exists()
        changed = old_hashes.get(pid) != h
        if changed or not image_exists:
            to_render.append(p)
        else:
            unchanged.append(p)

    return to_render, unchanged, new_hashes