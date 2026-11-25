"""Offline evaluation of the Sindbad recommender on the synthetic interactions.

Protocol (leave-one-out): for every synthetic buyer one interacted item is hidden. The models are fitted on the
remaining interactions, then asked to rank all items the buyer has not touched. We report HitRate@10 and NDCG@10
for the hidden item. Buyers are split in two halves: the blend weights are chosen on the first half (validation)
and the numbers in the table come from the second half (test).
Run:  python scripts/evaluate.py
"""
import csv, itertools, json, os, random, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from recommender import Recommender, EVENT_WEIGHTS  # noqa: E402
import make_synthetic  # noqa: E402

K = 10


def load():
    c = __import__('sqlite3').connect(os.path.join(ROOT, 'sindbad.db'))
    c.row_factory = __import__('sqlite3').Row
    products = [dict(r) for r in c.execute('SELECT id,title,category,tags FROM products ORDER BY id')]
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'data', 'synthetic_interactions.csv'))))
    return products, [(r['user_id'], int(r['product_id']), r['event_type']) for r in rows]


def split_holdout(inter, seed=11, keep=1.0):
    """Hide one interacted item per buyer. keep<1 additionally drops training rows to simulate sparse data."""
    rnd = random.Random(seed)
    by_user = {}
    for u, pid, ev in inter:
        by_user.setdefault(u, []).append((pid, ev))
    held, train = {}, []
    for u, items in by_user.items():
        pids = sorted({p for p, _ in items})
        h = rnd.choice(pids)
        held[u] = h
        kept = [(u, p, e) for p, e in items if p != h and (keep >= 1 or rnd.random() < keep)]
        if not kept:
            kept = [(u, p, e) for p, e in items if p != h][:1]
        train += kept
    return held, train, by_user


def score_users(model, users, train, held, method, weights=None):
    hist = {}
    for u, p, e in train:
        hist.setdefault(u, {}).setdefault(p, 0.0)
        hist[u][p] += EVENT_WEIGHTS[e]
    hits, ndcg = [], []
    rnd = random.Random(0)
    for u in users:
        if method == 'random':
            cand = [p for p in model.ids if p not in hist[u]]
            rnd.shuffle(cand)
            rank_list = cand[:K]
        else:
            w = {'content': {'content': 1}, 'item_knn': {'item_knn': 1}, 'svd': {'svd': 1}}.get(method, weights)
            if method == 'popularity':
                rank_list = [p for p, _ in model.recommend({}, 400) if p not in hist[u]][:K]
            else:
                rank_list = [p for p, _ in model.recommend(hist[u], K, w)]
        if held[u] in rank_list:
            r = rank_list.index(held[u])
            hits.append(1.0)
            ndcg.append(1.0 / np.log2(r + 2))
        else:
            hits.append(0.0)
            ndcg.append(0.0)
    return float(np.mean(hits)), float(np.mean(ndcg))


def run_once(products, inter, seed, keep):
    held, train, _ = split_holdout(inter, seed, keep)
    users = sorted(held)
    random.Random(seed).shuffle(users)
    val, test = users[: len(users) // 2], users[len(users) // 2:]
    model = Recommender().fit(products, train)
    grid = [dict(zip(('content', 'item_knn', 'svd'), (a / 4, b / 4, (4 - a - b) / 4))) for a, b in itertools.product(range(5), range(5)) if a + b <= 4]
    best = max(grid, key=lambda w: score_users(model, val, train, held, 'hybrid', w)[1])
    res = {m: score_users(model, test, train, held, m) for m in ['random', 'popularity', 'content', 'item_knn', 'svd']}
    res['hybrid'] = score_users(model, test, train, held, 'hybrid', best)
    return res, best, len(train)


def main():
    products, inter = load()
    out = {'items': len(products), 'synthetic_users': len({u for u, _, _ in inter}), 'interactions': len(inter), 'k': K, 'seeds': 5, 'scenarios': {}}
    for name, keep in [('full_data', 1.0), ('sparse_25pct', 0.25), ('very_sparse_10pct', 0.10)]:
        agg, ws, rows = {}, [], []
        for seed in range(5):
            res, best, n = run_once(products, inter, seed, keep)
            ws.append(best)
            rows.append(n)
            for m, (h, nd) in res.items():
                agg.setdefault(m, []).append((h, nd))
        table = {m: {'hit_rate@10': round(float(np.mean([a for a, _ in v])), 3), 'hit_std': round(float(np.std([a for a, _ in v])), 3), 'ndcg@10': round(float(np.mean([b for _, b in v])), 3)} for m, v in agg.items()}
        mean_w = {k: round(float(np.mean([w[k] for w in ws])), 2) for k in ws[0]}
        out['scenarios'][name] = {'train_rows_avg': int(np.mean(rows)), 'mean_blend_weights': mean_w, 'results': table}
    print(json.dumps(out, indent=1))
    os.makedirs(os.path.join(ROOT, 'docs'), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, 'docs', 'evaluation.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
