# Colinskis PokeDeals

Malta-focused Pokémon TCG price and stock comparison dashboard.

## Automation

- GitHub Pages serves `index.html`.
- The UI reads `data/catalog.json`.
- GitHub Actions runs four times per day and checks known Malta vendor listings.
- Confirmed price changes are written back automatically.
- A product is only auto-removed when a product-specific page explicitly reports it out of stock; ambiguous pages retain the last validated value.

## Vendor scope

PowerPlay, GamesPlus, Gamers Land, Gamebreaker, Mystical Tavern, Agenda, Forbidden Power, Exotique, itemCollect, Junior's, Toymagic and GamerZone.

## Cardmarket

Cardmarket values are market benchmarks, not guaranteed Malta-landed checkout quotes. The scanner does not fabricate seller-rating, shipping or delivery-time combinations that cannot be reliably verified.

## GitHub Pages

In **Settings → Pages**, choose **Deploy from a branch**, then `main` and `/ (root)`.

Public URL: `https://colinnr1.github.io/colinskis-pokedeals/`

## Manual refresh

Open **Actions → Refresh Pokemon deals → Run workflow**.
