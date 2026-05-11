# Pure+ Custom Catalog Feed Generator

Автоматизирана система за генериране на custom дизайнерски визии за продуктовия 
каталог на Pure+, използван в Meta Ads dynamic catalog campaigns.

## Какво прави

1. Изтегля оригиналния продуктов feed на Pure+ (WooCommerce XML)
2. За всеки продукт генерира custom изображение от HTML/CSS темплейт
3. Качва изображенията на GitHub Pages
4. Публикува нов XML feed с подменени image_link-ове
5. Meta Commerce Manager автоматично прибира новия feed по график

## Структура

- `src/` — Python скриптове (orchestrator, parser, renderer, feed builder)
- `templates/` — HTML/CSS темплейти за дизайна
- `assets/` — Logo, шрифтове, badge графики
- `config/` — YAML конфигурация (brand colors, badge rules, темплейт routing)
- `docs/` — Output (GitHub Pages serve-ва оттук): `feed.xml` + `images/`
- `.github/workflows/` — GitHub Actions автоматизация (cron daily run)

## Status

🚧 In development — Phase 1: Foundation
