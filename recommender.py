"""Hybrid product recommender for Sindbad (numpy only).

Three models are fitted at startup and blended:

* content:  TF-IDF vectors (unigrams + bigrams) over title, category and tags, compared with cosine similarity.
* item_knn: item-item collaborative filtering. Items are columns of the weighted user x item matrix and are
            compared with cosine similarity, so items bought or viewed by the same buyers score high.
* svd:      matrix factorisation. A truncated SVD of the user x item matrix gives latent item factors that are
            compared with cosine similarity. This links items that never co-occur directly.

The blend is a weighted sum of per-row min-max scaled scores. The weights come from a grid search on a
validation split (see scripts/evaluate.py and docs/evaluation.md).
"""
import re
import numpy as np

EVENT_WEIGHTS = {'view': 1.0, 'click': 1.7, 'cart': 3.5, 'favorite': 4.0, 'purchase': 5.0}
DEFAULT_WEIGHTS = {'content': 0.2, 'item_knn': 0.65, 'svd': 0.15}  # about the mean of the weights picked in docs/evaluation.json
STOP = {'and', 'for', 'the', 'with', 'of', 'in', 'a', 'to', 'by', 'on'}


def _stem(w):
    if len(w) > 4 and w.endswith('ies'):
        return w[:-3] + 'y'
    if len(w) > 3 and w.endswith('s') and not w.endswith('ss'):
        return w[:-1]
    return w


def tokenize(text):
    words = [_stem(w) for w in re.findall(r'[a-z0-9]+', (text or '').lower()) if w not in STOP]
    return words + [a + '_' + b for a, b in zip(words, words[1:])]


def product_text(p):
    """Title counts three times, category and tags twice. The description is generated boilerplate, so it is left out."""
    tags = (p.get('tags') or '').replace(',', ' ')
    return ' '.join([p.get('title', '')] * 3 + [p.get('category', '')] * 2 + [tags] * 2)


def tfidf_matrix(docs):
    toks = [tokenize(d) for d in docs]
    vocab = {}
    for t in toks:
        for w in t:
            vocab.setdefault(w, len(vocab))
    X = np.zeros((len(docs), len(vocab)))
    for i, t in enumerate(toks):
        for w in t:
            X[i, vocab[w]] += 1
    df = (X > 0).sum(axis=0)
    idf = np.log((1 + len(docs)) / (1 + df)) + 1.0
    X = np.where(X > 0, 1 + np.log(np.where(X > 0, X, 1)), 0) * idf
    n = np.linalg.norm(X, axis=1, keepdims=True)
    return X / np.where(n == 0, 1, n)


def cosine_rows(M):
    n = np.linalg.norm(M, axis=1, keepdims=True)
    M = M / np.where(n == 0, 1, n)
    S = M @ M.T
    np.fill_diagonal(S, 0.0)
    return S


def minmax_rows(S):
    lo = S.min(axis=1, keepdims=True)
    hi = S.max(axis=1, keepdims=True)
    return (S - lo) / np.where(hi - lo == 0, 1, hi - lo)


class Recommender:
    def __init__(self, k_factors=16):
        self.k = k_factors

    def fit(self, products, interactions):
        """products: list of dicts (id, title, category, tags). interactions: iterable of (user, product_id, event_type)."""
        self.ids = [p['id'] for p in products]
        self.index = {pid: i for i, pid in enumerate(self.ids)}
        self.products = {p['id']: p for p in products}
        n = len(self.ids)
        users = {}
        rows = []
        for u, pid, ev in interactions:
            if pid in self.index:
                rows.append((users.setdefault(u, len(users)), self.index[pid], EVENT_WEIGHTS.get(ev, 1.0)))
        R = np.zeros((max(len(users), 1), n))
        for u, i, w in rows:
            R[u, i] += w
        R = np.log1p(R)
        self.R = R
        self.popularity = R.sum(axis=0)
        self.S_content = cosine_rows(tfidf_matrix([product_text(p) for p in products]))
        self.S_knn = cosine_rows(R.T) if rows else np.zeros((n, n))
        if rows and min(R.shape) > 1:
            U, s, Vt = np.linalg.svd(R, full_matrices=False)
            k = min(self.k, len(s))
            self.S_svd = cosine_rows((Vt[:k].T * np.sqrt(s[:k])))
        else:
            self.S_svd = np.zeros((n, n))
        self.sims = {'content': minmax_rows(self.S_content), 'item_knn': minmax_rows(self.S_knn), 'svd': minmax_rows(self.S_svd)}
        return self

    def blend(self, weights=None):
        w = weights or DEFAULT_WEIGHTS
        return sum(w.get(k, 0.0) * m for k, m in self.sims.items())

    def similar(self, pid, k=6, weights=None):
        """Items most similar to one product, with the share each model contributed."""
        if pid not in self.index:
            return []
        i = self.index[pid]
        w = weights or DEFAULT_WEIGHTS
        total = self.blend(w)[i].copy()
        total[i] = -1
        out = []
        for j in np.argsort(-total)[:k]:
            parts = {name: float(w.get(name, 0.0) * self.sims[name][i, j]) for name in self.sims}
            out.append({'product_id': self.ids[j], 'score': round(float(total[j]), 4), 'parts': {a: round(b, 4) for a, b in parts.items()}})
        return out

    def recommend(self, history, k=10, weights=None):
        """history: {product_id: weight}. Personalised ranking; falls back to popularity when there is no usable history."""
        vec = np.zeros(len(self.ids))
        for pid, w in history.items():
            if pid in self.index:
                vec[self.index[pid]] += w
        if vec.sum() == 0:
            score = self.popularity.copy()
        else:
            score = (vec @ self.blend(weights)) / vec.sum()
        score[vec > 0] = -np.inf
        return [(self.ids[j], float(score[j])) for j in np.argsort(-score)[:k] if np.isfinite(score[j])]


def _explain(self, history, pid, weights=None):
    """The history item that contributed most to recommending pid (for the reason text)."""
    if pid not in self.index:
        return None
    j = self.index[pid]
    B = self.blend(weights)
    best, best_v = None, 0.0
    for q, w in history.items():
        if q in self.index and q != pid:
            v = w * B[self.index[q], j]
            if v > best_v:
                best, best_v = q, v
    return best


Recommender.explain = _explain


def load_synthetic(path):
    """Read data/synthetic_interactions.txt into (user, product_id, event_type) triples."""
    names = {'v': 'view', 'c': 'click', 'a': 'cart', 'p': 'purchase'}
    out = []
    with open(path) as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.split()
            for tok in parts[2:]:
                pid, ev = tok.split(':')
                out += [(parts[0], int(pid), names[ch]) for ch in ev]
    return out
