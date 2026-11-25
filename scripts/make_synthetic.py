"""Generate labelled SYNTHETIC buyer interactions for Sindbad.

The platform has almost no real traffic, so a collaborative model has nothing to learn from. This script plants
eight buyer segments (hotel procurement, construction site, office IT, ...). Each segment buys across several
categories, the way real procurement bundles do. Buyers pick mostly from their own segment plus some random noise.
The file is clearly synthetic: every row carries its segment label. Results measured on it show that the models
can recover planted structure. They do not show how well they would do on real buyers.
Run:  python scripts/make_synthetic.py
"""
import os, random, sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEGMENTS = {
    'hotel_procurement': ['towel', 'bathrobe', 'bed linen', 'mattress protector', 'coffee mug', 'tableware', 'serving tray', 'beverage dispenser', 'cleaning cloth', 'olive oil extra', 'coffee beans', 'cookware', 'storage container'],
    'construction_site': ['safety helmet', 'safety glove', 'work boot', 'safety vest', 'goggles', 'harness', 'earmuff', 'coverall', 'welding', 'workwear jacket', 'water pump', 'generator', 'air compressor', 'hydraulic jack'],
    'office_it': ['usb-c hub', 'wi-fi access', 'network switch', 'patch cable', 'poe network', 'server cabinet', 'ssd', 'touch monitor', 'security camera', 'desk lamp', 'office chair', 'conference speaker', 'receipt printer', 'barcode scanner', 'led panel'],
    'food_importer': ['dried dates', 'basmati', 'olive oil', 'strawberry', 'mango', 'cashew', 'coffee beans', 'hibiscus', 'sesame', 'okra', 'tomato paste', 'lentils', 'honey', 'fava', 'onion flakes', 'aluminium food', 'pet plastic', 'shipping carton'],
    'retail_ecommerce': ['shopping bag', 'kraft paper', 'mailer', 'shipping carton', 'tote', 'cotton t-shirt', 'hoodie', 'polo', 'bubble', 'zip-lock', 'stretch wrapping', 'tamper', 'jute', 'folding carton', 'water bottle'],
    'outdoor_sports': ['camping led', 'sleeping bag', 'folding chair', 'cooler', 'trekking', 'dry bag', 'camping table', 'dumbbell', 'jump rope', 'cycling helmet', 'resistance band', 'resistance training', 'yoga', 'football', 'solar street'],
    'healthcare_cleaning': ['medical gown', 'first aid', 'respirator', 'face shield', 'shoe cover', 'microfiber', 'safety glove', 'goggles', 'mattress protector', 'towel', 'bathrobe'],
    'factory_maintenance': ['water pump', 'electric motor', 'hydraulic hose', 'pneumatic', 'pipe fitting', 'welding', 'conveyor', 'bearing', 'pressure gauge', 'hydraulic jack', 'air compressor', 'energy meter', 'copper electrical', 'aluminium profile', 'workwear jacket', 'safety glove'],
}


def load_products():
    c = sqlite3.connect(os.path.join(ROOT, 'sindbad.db'))
    rows = c.execute('SELECT id,title FROM products ORDER BY id').fetchall()
    c.close()
    return rows


def segment_items(products):
    out = {}
    for seg, keys in SEGMENTS.items():
        ids = [pid for pid, title in products if any(k in title.lower() for k in keys)]
        assert len(ids) >= 8, (seg, ids)
        out[seg] = ids
    return out


def generate(n_users=480, seed=7):
    rnd = random.Random(seed)
    products = load_products()
    segs = segment_items(products)
    all_ids = [pid for pid, _ in products]
    rows = []
    names = list(segs)
    for u in range(n_users):
        seg = names[u % len(names)]
        pool = segs[seg]
        weights = [1.0 / (1 + (k % 5)) for k in range(len(pool))]
        n_items = rnd.randint(6, 12)
        picked = set()
        while len(picked) < n_items:
            picked.add(rnd.choices(pool, weights)[0] if rnd.random() < 0.85 else rnd.choice(all_ids))
        for pid in sorted(picked):
            rows.append((f'syn{u}', pid, 'view', names.index(seg)))
            if rnd.random() < 0.5: rows.append((f'syn{u}', pid, 'click', names.index(seg)))
            if rnd.random() < 0.3: rows.append((f'syn{u}', pid, 'cart', names.index(seg)))
            if rnd.random() < 0.15: rows.append((f'syn{u}', pid, 'purchase', names.index(seg)))
    return rows


if __name__ == '__main__':
    rows = generate()
    code = {'view': 'v', 'click': 'c', 'cart': 'a', 'purchase': 'p'}
    users = {}
    for u, pid, ev, seg in rows:
        users.setdefault(u, [seg, {}])[1].setdefault(pid, '')
        users[u][1][pid] += code[ev]
    os.makedirs(os.path.join(ROOT, 'data'), exist_ok=True)
    with open(os.path.join(ROOT, 'data', 'synthetic_interactions.txt'), 'w') as f:
        f.write('# SYNTHETIC data. line = user segment_index product_id:events ... (v view, c click, a cart, p purchase)\n')
        for u, (seg, items) in users.items():
            f.write(u + ' ' + str(seg) + ' ' + ' '.join(f'{p}:{e}' for p, e in sorted(items.items())) + '\n')
    print(len(rows), 'events,', len(users), 'synthetic users')
