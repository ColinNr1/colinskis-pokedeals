#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'data' / 'catalog.json'

DIRECT = {
 ('chaos-half','Agenda'): 'https://agendabookshop.com/products/half-booster-box-factory-sealed-18-booster-packs',
 ('chaos-half','Gamebreaker'): 'https://gamebreakermalta.com/product/pokemon-chaos-rising-half-booster-box-18-pk-sealed/',
 ('chaos-half','Gamers Land'): 'https://gamersland.com.mt/product/pokemon-tcg-mega-evolution-chaos-rising-half-booster-box/',
 ('pitch-half','Agenda'): 'https://agendabookshop.com/products/pitch-black-half-booster-box',
 ('pitch-half','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-pitch-black-half-booster-box/',
 ('pitch-half','Gamebreaker'): 'https://gamebreakermalta.com/product/pokemon-tcg-pitch-black-half-booster-box/',
 ('pitch-pack','Agenda'): 'https://agendabookshop.com/products/pitch-black-booster',
 ('pitch-pack','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-pitch-black-booster-pack-2/',
 ('chaos-pack','Agenda'): 'https://agendabookshop.com/products/pokemon-45-chaos-rising',
 ('chaos-pack','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-chaos-rising-booster-pack/',
 ('perfect-pack','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-perfect-order-booster-pack/',
 ('perfect-half','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-perfect-order-half-booster-box/',
 ('chaos-bundle','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-chaos-rising-booster-bundle/',
 ('pitch-etb','Gamebreaker'): 'https://gamebreakermalta.com/product/pokemon-tcg-mega-evolution-pitch-black-elite-trainer-box/',
 ('perfect-etb','Gamers Land'): 'https://gamersland.com.mt/product/pokemon-tcg-perfect-order-elite-trainer-box/',
 ('perfect-etb','Gamebreaker'): 'https://gamebreakermalta.com/product/pokemon-mega-evolution-perfect-order-elite-trainer-box/',
 ('perfect-etb','Exotique'): 'https://exotique.com.mt/product/pokemon-tcg-mega-evolution-perfect-order-elite-trainer-box/',
 ('chaos-etb','Gamers Land'): 'https://gamersland.com.mt/product/pokemon-tcg-mega-evolution-chaos-rising-elite-trainer-box-etb/',
 ('phantasmal-etb','Exotique'): 'https://exotique.com.mt/product/pokemon-tcg-mega-evolution-phantasmal-flames-elite-trainer-box/',
 ('mega-zygarde','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-mega-zygarde-ex-premium-collection/',
 ('iono','Gamebreaker'): 'https://gamebreakermalta.com/product/pokemon-tcg-ionos-bellibolt-ex-premium-collection/',
 ('iono','PowerPlay'): 'https://www.powerplaymt.com/product-page/iono-s-bellibolt-ex',
 ('perfect-3pack','Gamebreaker'): 'https://gamebreakermalta.com/product/pokemon-tcg-perfect-order-3-pack-blister/',
 ('perfect-3pack','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-perfect-order-3-pack-blister/',
 ('chaos-check','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-chaos-rising-checklane-blister/',
 ('chaos-premcheck','Gamebreaker'): 'https://gamebreakermalta.com/product/pokemon-tcg-mega-evolution-chaos-rising-premium-checklane-blister-pawmot/',
 ('chaos-premcheck','Mystical Tavern'): 'https://mysticaltavern.com/product/pokemon-tcg-mega-evolution-chaos-rising-premium-checklane/',
 ('chaos-premcheck','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-chaos-rising-premium-checklane-blister/',
 ('destined-pack','Gamers Land'): 'https://gamersland.com.mt/product/destined-rivals-booster-pack/',
 ('destined-half','Gamers Land'): 'https://gamersland.com.mt/product/destined-rivals-half-booster-box/',
 ('lost-origin-sleeved','Gamers Land'): 'https://gamersland.com.mt/product/sword-shield-lost-origin-sleeved-booster-pack/',
 ('astral-pack','Gamers Land'): 'https://gamersland.com.mt/product/sword-shield-astral-radiance-booster-pack/',
 ('worlds2024','Gamebreaker'): 'https://gamebreakermalta.com/product/pokemon-tcg-world-championships-deck-2024/',
 ('worlds2024','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-world-championships-deck-2024/',
 ('pitch-sleeved','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-pitch-black-sleeved-booster-pack/',
 ('chaos-sleeved','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-chaos-rising-sleeved-booster-pack/',
 ('perfect-sleeved','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-perfect-order-sleeved-booster-pack/',
 ('chaos-3pack','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-chaos-rising-3-booster-blister-pack/',
 ('pitch-3pack','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-pitch-black-3-booster-blister-pack/',
 ('pitch-3pack','Mystical Tavern'): 'https://mysticaltavern.com/product/pokemon-tcg-mega-evolution-pitch-black-3-pack/',
 ('perfect-checklane','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-perfect-order-checklane-blister/',
 ('perfect-premcheck','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-perfect-order-premium-checklane-blister/',
 ('lucario-league','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-mega-lucario-ex-league-battle-deck/',
 ('journey-pack','GamesPlus'): 'https://gamesplusmalta.com/product/pokemon-tcg-scarlet-violet-9-journey-together-booster-pack/',
 ('moonlit-tin','Mystical Tavern'): 'https://mysticaltavern.com/product/pokemon-tcg-mega-moonlit-tins/',
 ('my-first-battle','Mystical Tavern'): 'https://mysticaltavern.com/product/pokemon-tcg-my-first-battle-bulbasaur-vs-pikachu-charmander-vs-squirtle/',
 ('corviknight-battle','Mystical Tavern'): 'https://mysticaltavern.com/product/pokemon-tcg-corviknight-v-battle-deck/',
 ('lycanroc-battle','Mystical Tavern'): 'https://mysticaltavern.com/product/pokemon-tcg-lycanroc-v-battle-deck/',
}

REMOVE = {
 ('phantasmal-etb','Gamers Land'),
 ('meganium','PowerPlay'),
 ('emboar','PowerPlay'),
 ('kingambit','PowerPlay'),
 ('first-partner-s3','Gamebreaker'),
}

def main():
    data = json.loads(CATALOG.read_text(encoding='utf-8'))
    changed = 0
    removed = 0
    for product in data.get('products', []):
        kept = []
        for listing in product.get('listings', []):
            key = (product.get('id'), listing.get('store'))
            if key in REMOVE:
                removed += 1
                continue
            if key in DIRECT and listing.get('url') != DIRECT[key]:
                listing['url'] = DIRECT[key]
                changed += 1
            listing['direct_product_url'] = '/product/' in listing.get('url','') or '/product-page/' in listing.get('url','') or '/products/' in listing.get('url','')
            kept.append(listing)
        product['listings'] = kept
    data['products'] = [p for p in data.get('products', []) if p.get('listings')]
    data.setdefault('scan_summary', {})['scanner_version'] = '1.1-direct-links'
    CATALOG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Normalized {changed} listing URLs; removed {removed} stale listings')

if __name__ == '__main__':
    main()
