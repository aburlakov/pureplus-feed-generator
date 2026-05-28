"""
main.py — Orchestrator
─────────────────────────────────────────────────────────────
Свързва целия pipeline:
  fetch feed → split (cache) → batch render → build new feed → save cache

Локално: python -m src.main
"""
from src.fetch_feed import fetch_feed_xml, parse_feed
from src.cache import split_products, save_cache
from src.batch_render import render_batch
from src.build_feed import build_feed
from dataclasses import asdict
from pathlib import Path


def product_to_dict(p):
    d = asdict(p)
    d.pop("raw_xml", None)
    return d


def main():
    print("=" * 60)
    print("🚀 PURE+ Feed Generator — стартиране")
    print("=" * 60)

    # 1. Изтегляне + парсване
    xml = fetch_feed_xml()
    products_obj = parse_feed(xml)
    products = [product_to_dict(p) for p in products_obj]

    if not products:
        print("⚠️  Няма продукти. Спирам.")
        return

    # 2. Филтрираме out-of-stock
    in_stock = [p for p in products if p.get("availability") == "in stock"]
    print(f"📦 {len(in_stock)} продукта в наличност (от {len(products)} общо)")

    # 3. Cache split
    to_render, unchanged, new_hashes = split_products(in_stock)
    print(f"🔄 За рендериране: {len(to_render)} | Непроменени: {len(unchanged)}")

    # 4. Batch render
    succeeded, failed = render_batch(to_render)

    # 5. Build new feed
    # Събираме всички product IDs, които имат генерирано изображение
    # (всички unchanged + всички, които току-що се рендерираха успешно)
    rendered_ids = set(p["id"] for p in unchanged) | set(succeeded)
    
    kept, skipped = build_feed(xml, rendered_ids)

    # 6. Записваме cache само ако няма провали
    if not failed:
        save_cache(new_hashes)
        print("💾 Cache обновен.")
    else:
        print("⚠️  Има провали — cache НЕ е обновен (ще re-try утре).")

    print("\n✅ Pipeline завършен.")
    print(f"📡 Feed готов на: docs/feed.xml")


if __name__ == "__main__":
    main()