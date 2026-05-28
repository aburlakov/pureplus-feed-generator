"""
fetch_feed.py
─────────────────────────────────────────────────────────────
Изтегля оригиналния продуктов XML feed от Pure+ (WooCommerce),
парсва го и връща списък от Product обекти със структурирани данни.

Това е първият модул в pipeline-а. Останалите модули
(badge_logic, render, build_feed) работят с резултата от тук.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import httpx
from lxml import etree
import json
from pathlib import Path


# ─────────────────────────────────────────────────────────────
# КОНФИГУРАЦИЯ
# ─────────────────────────────────────────────────────────────
# URL към оригиналния feed на Pure+.
# По-късно ще преместим това в config/settings.yaml,
# но засега го държим тук за простота.
FEED_URL = "https://pureplus.bg/wp-content/uploads/woo-product-feed-pro/xml/7i614t6chm0ipgkamljtn5sutl0h84ym.xml"

# Timeout при изтеглянето - 30 секунди е достатъчно за feed под 100 продукта
REQUEST_TIMEOUT = 30


# ─────────────────────────────────────────────────────────────
# DATA STRUCTURE
# ─────────────────────────────────────────────────────────────
# Product е dataclass — Python начин за дефиниране на структурирани
# обекти с типизирани полета. Това ни дава autocomplete и type checking.
#
# Всяко поле тук съответства на елемент от Google Merchant / Facebook
# product feed спецификацията. Полетата, които не са задължителни,
# са Optional и могат да бъдат None.

@dataclass
class Product:
    # Задължителни полета (Meta изисква тези за всеки продукт)
    id: str                                  # Уникален ID
    title: str                               # Име на продукта
    description: str                         # Описание
    link: str                                # URL към продуктовата страница
    image_link: str                          # Главна снимка
    availability: str                        # in stock / out of stock
    price: str                               # Текуща цена (string, с валута)

    # Optional полета (не всеки продукт ги има)
    sale_price: Optional[str] = None         # Промо цена
    brand: Optional[str] = None              # Марка
    product_type: Optional[str] = None       # Категория
    google_product_category: Optional[str] = None
    condition: Optional[str] = None          # new / used / refurbished
    gtin: Optional[str] = None               # Глобален баркод
    mpn: Optional[str] = None                # Manufacturer Part Number
    additional_image_links: list[str] = field(default_factory=list)

    # Computed полета (изчисляваме ги от другите)
    price_value: Optional[float] = None      # Числова стойност на price
    sale_price_value: Optional[float] = None # Числова стойност на sale_price
    discount_percent: Optional[int] = None   # Изчислен процент намаление

    # Raw XML (запазваме оригиналния item елемент за build_feed.py)
    raw_xml: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────
def _extract_text(element, tag: str, namespaces: dict) -> Optional[str]:
    """
    Извлича текст от под-елемент на даден item.
    Връща None ако елементът липсва или е празен.
    
    Защо ни трябва: в продуктовия feed повечето елементи са в
    namespace 'g:' (g:id, g:title, g:price). Тази функция
    скрива namespace handling-а от main кода.
    """
    found = element.find(f"g:{tag}", namespaces=namespaces)
    if found is None:
        # Опитваме без namespace (някои feed-ове не ползват prefix)
        found = element.find(tag)
    if found is None or found.text is None:
        return None
    return found.text.strip()


def _parse_price(price_str: Optional[str]) -> Optional[float]:
    """
    Парсва price string като '59.90 BGN' и връща числова стойност 59.90.
    Връща None ако price е невалиден.
    
    Защо ни трябва: цените във feed-а са string ('59.90 BGN' или '59,90 лв.'),
    но за изчисления (% намаление) ни трябва число.
    """
    if not price_str:
        return None
    # Премахваме валута, спейсове, заменяме запетая с точка
    cleaned = (
        price_str.replace("BGN", "")
                 .replace("лв.", "")
                 .replace("лв", "")
                 .replace(",", ".")
                 .strip()
    )
    try:
        return float(cleaned)
    except ValueError:
        return None


def _calculate_discount(price: Optional[float], sale: Optional[float]) -> Optional[int]:
    """
    Изчислява процент намаление спрямо обикновената цена.
    Връща None ако няма sale_price или ако намалението е 0%.
    """
    if not price or not sale or sale >= price:
        return None
    discount = round((1 - sale / price) * 100)
    return discount if discount > 0 else None


# ─────────────────────────────────────────────────────────────
# MAIN FETCH & PARSE
# ─────────────────────────────────────────────────────────────
def fetch_feed_xml(url: str = FEED_URL) -> bytes:
    """
    Изтегля raw XML съдържанието на feed-а.
    Връща bytes (не string), защото lxml предпочита bytes за parsing.
    """
    print(f"📥 Изтеглям feed от: {url}")
    with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()  # Хвърля грешка ако HTTP статус != 200
    print(f"✅ Успешно изтеглени {len(response.content):,} bytes")
    return response.content


def parse_feed(xml_content: bytes) -> list[Product]:
    """
    Парсва XML feed-а и връща списък от Product обекти.
    """
    print("🔍 Парсвам XML структурата...")
    
    # lxml.etree.fromstring парсва bytes-овете в дърво от елементи
    root = etree.fromstring(xml_content)
    
    # Извличаме namespace декларацията. В Google/Facebook feed-овете
    # повечето елементи са в namespace 'http://base.google.com/ns/1.0'
    # с prefix 'g:'
    namespaces = {"g": "http://base.google.com/ns/1.0"}
    
    # Намираме всички <item> елементи (всеки item = един продукт)
    # В RSS-базиран feed те са под <channel>
    items = root.findall(".//item")
    
    if not items:
        # Fallback за feed-ове, които не следват RSS структурата
        items = root.findall(".//product")
    
    print(f"📦 Намерени {len(items)} продукта в feed-а")
    
    products = []
    for item in items:
        # Извличаме всички полета чрез helper-а
        product = Product(
            id=_extract_text(item, "id", namespaces) or "",
            title=_extract_text(item, "title", namespaces) or "",
            description=_extract_text(item, "description", namespaces) or "",
            link=_extract_text(item, "link", namespaces) or "",
            image_link=_extract_text(item, "image_link", namespaces) or "",
            availability=_extract_text(item, "availability", namespaces) or "",
            price=_extract_text(item, "price", namespaces) or "",
            sale_price=_extract_text(item, "sale_price", namespaces),
            brand=_extract_text(item, "brand", namespaces),
            product_type=_extract_text(item, "product_type", namespaces),
            google_product_category=_extract_text(item, "google_product_category", namespaces),
            condition=_extract_text(item, "condition", namespaces),
            gtin=_extract_text(item, "gtin", namespaces),
            mpn=_extract_text(item, "mpn", namespaces),
        )
        
        # Допълнителни снимки (могат да са няколко в един item)
        additional = item.findall("g:additional_image_link", namespaces=namespaces)
        product.additional_image_links = [el.text.strip() for el in additional if el.text]
        
        # Computed полета
        product.price_value = _parse_price(product.price)
        product.sale_price_value = _parse_price(product.sale_price)
        product.discount_percent = _calculate_discount(
            product.price_value, 
            product.sale_price_value
        )
        
        # Запазваме оригиналния XML, за да го ползваме после в build_feed.py
        product.raw_xml = etree.tostring(item, encoding="unicode")
        
        products.append(product)
    
    return products


# ─────────────────────────────────────────────────────────────
# ENTRY POINT (тестване от командния ред)
# ─────────────────────────────────────────────────────────────
# Когато run-ваш този файл директно (python -m src.fetch_feed),
# изпълнява се блокът отдолу. Когато друг файл го import-ва,
# не се изпълнява. Това е стандартен Python pattern.

def main():
    """
    Тестов entry point — изтегля feed-а, парсва го, и записва
    sample JSON в cache/, за да можем да го прегледаме на спокойствие.
    """
    # Стъпка 1: Изтегляне
    xml_content = fetch_feed_xml()
    
    # Стъпка 2: Парсване
    products = parse_feed(xml_content)
    
    if not products:
        print("⚠️  Внимание: не са намерени продукти. Провери XML структурата.")
        return
    
    # Стъпка 3: Печатаме обобщение в конзолата
    print("\n" + "=" * 60)
    print("📊 ОБОБЩЕНИЕ")
    print("=" * 60)
    print(f"Общо продукти: {len(products)}")
    
    in_stock = sum(1 for p in products if p.availability == "in stock")
    on_sale = sum(1 for p in products if p.discount_percent)
    with_brand = sum(1 for p in products if p.brand)
    
    print(f"В наличност: {in_stock}")
    print(f"С активно намаление: {on_sale}")
    print(f"С попълнена марка: {with_brand}")
    
    # Стъпка 4: Записваме sample JSON за inspection
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)
    
    sample_path = cache_dir / "products_sample.json"
    
    # Конвертираме dataclass-овете в dict-ове за JSON serialization.
    # Изключваме raw_xml, защото е дълъг и затормозява четенето.
    products_dict = []
    for p in products[:5]:  # Само първите 5 за sample
        d = asdict(p)
        d.pop("raw_xml", None)
        products_dict.append(d)
    
    with open(sample_path, "w", encoding="utf-8") as f:
        json.dump(products_dict, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Sample (първите 5 продукта) записан в: {sample_path}")
    
    # Стъпка 5: Показваме първия продукт за visual check
    print("\n" + "=" * 60)
    print("🔍 ПРИМЕРЕН ПРОДУКТ (първият от feed-а)")
    print("=" * 60)
    first = products[0]
    print(f"ID:              {first.id}")
    print(f"Title:           {first.title}")
    print(f"Brand:           {first.brand}")
    print(f"Price:           {first.price} (parsed: {first.price_value})")
    print(f"Sale price:      {first.sale_price} (parsed: {first.sale_price_value})")
    print(f"Discount:        {first.discount_percent}%" if first.discount_percent else "Discount:        няма")
    print(f"Availability:    {first.availability}")
    print(f"Category:        {first.product_type}")
    print(f"Image:           {first.image_link}")


if __name__ == "__main__":
    main()