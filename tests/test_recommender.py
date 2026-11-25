import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from recommender import Recommender, tfidf_matrix, tokenize, minmax_rows

PRODUCTS = [
    {'id': 1, 'title': 'Safety helmets', 'category': 'Safety', 'tags': 'safety,head'},
    {'id': 2, 'title': 'Safety gloves', 'category': 'Safety', 'tags': 'safety,hand'},
    {'id': 3, 'title': 'Cotton towels', 'category': 'Textiles', 'tags': 'cotton,hotel'},
    {'id': 4, 'title': 'Cotton bathrobes', 'category': 'Textiles', 'tags': 'cotton,hotel'},
    {'id': 5, 'title': 'Water pumps', 'category': 'Industrial', 'tags': 'pump'},
]


def test_tokenizer_stems_and_makes_bigrams():
    t = tokenize('Safety gloves for the site')
    assert 'glove' in t and 'safety_glove' in t and 'the' not in t


def test_tfidf_rows_are_unit_length_and_related_titles_are_closer():
    X = tfidf_matrix(['safety helmet', 'safety glove', 'cotton towel'])
    assert np.allclose(np.linalg.norm(X, axis=1), 1)
    assert X[0] @ X[1] > X[0] @ X[2]


def test_content_model_finds_same_category_item():
    m = Recommender().fit(PRODUCTS, [])
    assert m.similar(1, 1, {'content': 1})[0]['product_id'] == 2
    assert m.similar(3, 1, {'content': 1})[0]['product_id'] == 4


def test_collaborative_model_learns_cross_category_pairs():
    # buyers of helmets also buy pumps, so CF should link 1 and 5 although the text does not
    inter = [(f'u{i}', p, 'purchase') for i in range(20) for p in (1, 5)] + [(f'v{i}', p, 'purchase') for i in range(20) for p in (3, 4)]
    m = Recommender(k_factors=2).fit(PRODUCTS, inter)
    assert m.similar(1, 1, {'item_knn': 1})[0]['product_id'] == 5
    assert m.similar(1, 1, {'svd': 1})[0]['product_id'] == 5


def test_recommend_excludes_seen_items_and_falls_back_to_popularity():
    inter = [('a', 1, 'view'), ('a', 5, 'view'), ('b', 3, 'purchase'), ('c', 3, 'purchase')]
    m = Recommender(k_factors=2).fit(PRODUCTS, inter)
    recs = [p for p, _ in m.recommend({1: 1.0}, 5)]
    assert 1 not in recs
    assert m.recommend({}, 1)[0][0] == 3


def test_minmax_rows_range():
    S = minmax_rows(np.array([[0., 2., 4.], [1., 1., 1.]]))
    assert S[0].min() == 0 and S[0].max() == 1 and np.all(S[1] == 0)


def test_evaluation_beats_popularity_on_synthetic_data():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
    import evaluate
    products, inter = evaluate.load()
    res, _, _ = evaluate.run_once(products, inter, seed=0, keep=1.0)
    assert res['hybrid'][0] > res['popularity'][0] + 0.2
    assert res['hybrid'][0] > res['content'][0]
