"""
build_feed.py — Генерира новия XML feed
─────────────────────────────────────────────────────────────
Чете оригиналния XML, подменя image_link на всеки продукт с
GitHub Pages URL, запазва оригинала като additional_image_link,
филтрира продукти без рендерирано изображение, и записва
новия feed в docs/feed.xml за GitHub Pages.

Този XML е това, което Meta Commerce Manager ще fetch-ва.
"""
import html
from pathlib import Path
from lxml import etree
from config.settings import IMAGES_BASE_URL, FEED_OUTPUT


# Google Merchant namespace — всички полета (g:id, g:price, etc.)
NAMESPACES = {"g": "http://base.google.com/ns/1.0"}
G_NS = "{http://base.google.com/ns/1.0}"

# Полета, които source feed-ът понякога двойно енкодира (&amp;gt; вместо &gt;).
# html.unescape ги нормализира преди запис, за да ги прочете Meta правилно.
FIELDS_TO_NORMALIZE = ["product_type", f"{G_NS}title", "title", "description"]


def _normalize_encoding(item):
    """
    Неутрализира двойно енкодиране в текстови полета.
    Source feed-ът от AdTribes понякога съдържа &amp;gt; вместо &gt;,
    което без поправка стига до Meta като видим '&gt;' в текста.
    """
    for tag in FIELDS_TO_NORMALIZE:
        el = item.find(tag)
        if el is not None and el.text:
            el.text = html.unescape(el.text)


def build_feed(original_xml: bytes, rendered_ids: set, output_path=FEED_OUTPUT):
    """
    Изгражда новия XML feed.

    Args:
        original_xml: raw bytes на оригиналния feed от Pure+
        rendered_ids: set от product IDs, които имат генерирано изображение
        output_path: къде да запишем резултата

    Returns:
        (kept_count, skipped_count) tuple
    """
    print("🔨 Изграждам новия XML feed...")

    parser = etree.XMLParser(remove_blank_text=False, recover=True)
    root = etree.fromstring(original_xml, parser=parser)

    items = root.findall(".//item")
    if not items:
        items = root.findall(".//product")

    kept = 0
    skipped = 0
    items_to_remove = []

    for item in items:
        # Product ID
        id_elem = item.find(f"{G_NS}id")
        if id_elem is None:
            id_elem = item.find("id")

        if id_elem is None or id_elem.text is None:
            items_to_remove.append(item)
            skipped += 1
            continue

        product_id = id_elem.text.strip()

        # Без рендерирано изображение → изхвърляме от feed-а
        if product_id not in rendered_ids:
            items_to_remove.append(item)
            skipped += 1
            continue

        # Нормализираме двойно енкодирани текстови полета
        _normalize_encoding(item)

        # Подменяме image_link, запазваме оригинала като additional
        image_elem = item.find(f"{G_NS}image_link")
        if image_elem is None:
            image_elem = item.find("image_link")

        if image_elem is not None and image_elem.text:
            original_image_url = image_elem.text.strip()
            image_elem.text = f"{IMAGES_BASE_URL}/{product_id}.jpg"

            additional = etree.SubElement(item, f"{G_NS}additional_image_link")
            additional.text = original_image_url

        kept += 1

    for item in items_to_remove:
        item.getparent().remove(item)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tree = etree.ElementTree(root)
    tree.write(
        str(output_path),
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    )

    file_size = output_path.stat().st_size
    print(f"✅ Feed записан: {output_path}")
    print(f"   Запазени: {kept} продукта")
    print(f"   Пропуснати: {skipped} (без рендер / out-of-stock)")
    print(f"   Размер: {file_size:,} bytes")

    return kept, skipped