"""
render.py — Rendering engine
─────────────────────────────────────────────────────────────
Рендерира продукт от template_a.html чрез Playwright.

  • render_one()    — рендерира един продукт в подадена page (за batch)
  • build_context() — мапва продукт → template променливи

Auto-fit: вместо да гадаем font-size по брой символи, реално
МЕРИМ дали заглавието прелива (хоризонтално или вертикално) и
намаляваме шрифта стъпка по стъпка докато се събере. Така нито
едно заглавие никога не прелива, независимо от съдържанието.
"""
import html as html_lib
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from PIL import Image


# ── Presentation helpers ─────────────────────────────────

def clean_category(product_type):
    """'Home &gt; Решения за кухня' -> 'Решения за кухня' (последна част)."""
    if not product_type:
        return ""
    decoded = html_lib.unescape(product_type)
    parts = [p.strip() for p in decoded.split(">")]
    return parts[-1] if parts else ""


def format_price(value):
    """299.0 -> '299.00 €' (точка, символ след, интервал)."""
    if value is None:
        return ""
    return f"{value:.2f} €"


def build_context(product):
    """Мапва raw продукт (dict) в template променливи."""
    price_v = product.get("price_value")
    sale_v = product.get("sale_price_value")
    discount = product.get("discount_percent")
    has_discount = bool(sale_v and discount)

    return {
        "title": product["title"],
        "title_font_size": 76,   # стартов размер; JS auto-fit го коригира
        "category": clean_category(product.get("product_type")),
        "image_link": product["image_link"],
        "has_discount": has_discount,
        "discount_percent": discount,
        "price_display": format_price(price_v),
        "current_price_display": format_price(sale_v if has_discount else price_v),
    }


# ── Auto-fit JS ──────────────────────────────────────────
# Намалява font-size на .pp-name докато нито хоризонтално,
# нито вертикално не прелива. Връща финалния размер.
_AUTOFIT_JS = """
() => {
  // Свиваме заглавието докато се събере в наличната зона
  // (.pp-name е flexible box в grid-а; .pp-name-text е текстът).
  // Мерим И височина, И ширина спрямо реалната налична зона.
  const box = document.querySelector('.pp-name');
  const txt = document.querySelector('.pp-name-text');
  if (!box || !txt) return 0;
  const maxSize = 64, minSize = 20;
  let size = maxSize;
  txt.style.fontSize = size + 'px';
  const fits = () => (txt.scrollHeight <= box.clientHeight + 1) &&
                     (txt.scrollWidth  <= box.clientWidth + 1);
  let guard = 0;
  while (!fits() && size > minSize && guard < 120) {
    size -= 1;
    txt.style.fontSize = size + 'px';
    guard++;
  }
  return size;
}
"""


# ── Template loading (веднъж, кешира се) ─────────────────

_ENV = None
_TEMPLATE = None

def _get_template(templates_dir="templates"):
    global _ENV, _TEMPLATE
    if _TEMPLATE is None:
        _ENV = Environment(loader=FileSystemLoader(templates_dir))
        _TEMPLATE = _ENV.get_template("template_a.html")
    return _TEMPLATE


# ── Single render ────────────────────────────────────────

def render_one(product, page, out_dir, templates_dir="templates", tmp_dir="cache"):
    """
    Рендерира ЕДИН продукт в подадена Playwright page.
    Връща пътя към генерирания JPG.
    """
    template = _get_template(templates_dir)
    ctx = build_context(product)
    html_out = template.render(**ctx)

    tmp_dir = Path(tmp_dir)
    tmp_dir.mkdir(exist_ok=True)
    tmp_html = tmp_dir / f"_render_{product['id']}.html"

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / f"{product['id']}.png"
    jpg_path = out_dir / f"{product['id']}.jpg"

    try:
        tmp_html.write_text(html_out, encoding="utf-8")
        page.goto(f"file://{tmp_html.resolve()}")
        page.wait_for_timeout(2000)      # шрифтове + продуктова снимка
        page.evaluate(_AUTOFIT_JS)       # auto-fit на заглавието
        page.wait_for_timeout(200)       # стабилизиране след resize
        page.locator(".pp-banner").screenshot(path=str(png_path))

        img = Image.open(png_path).convert("RGB")
        img.save(jpg_path, "JPEG", quality=88, optimize=True)
    finally:
        png_path.unlink(missing_ok=True)
        tmp_html.unlink(missing_ok=True)

    return jpg_path