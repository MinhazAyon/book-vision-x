# core/evaluation/performance.py

# --- Third-party imports ---
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

def evaluate(data: pd.DataFrame, matrix: np.ndarray, recom_n: int):
    """
    Evaluation of top-K recommendations using sparse binary matrices.
    Returns a DataFrame with metrics: Precision@K, HitRate@K, MAP@K, NDCG@K
    """
    # # Build binary attribute matrix
    # for col in ['genres', 'writer', 'director', 'cast']:
    #     data[col] = data[col].fillna('').str.replace(' ', ', ')

    # Get columns without numbers       
    text_cols = data.select_dtypes(exclude=np.number).columns.tolist()

    # Create a unique list of all attributes
    attr_set = set()
    for col in text_cols:
        attr_set.update(','.join(data[col]).split(','))
    attr_set.discard('')  # remove empty string
    attr_list = sorted(list(attr_set))
    attr_index = {a: idx for idx, a in enumerate(attr_list)}

    n_movies = len(data)
    n_attrs = len(attr_list)

    # Build sparse matrix (movies x attributes)
    rows, cols = [], []
    for i in range(n_movies):
        attrs = set()
        for col in text_cols:
            attrs.update(a.strip() for a in data.iloc[i][col].split(',') if a.strip())
        for a in attrs:
            if a in attr_index:
                rows.append(i)
                cols.append(attr_index[a])
    M = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n_movies, n_attrs), dtype=np.int8)

    # Compute ground-truth intersection counts
    ## Binary matrix multiplication: intersection count per pair
    intersect_count = M.dot(M.T).toarray()  # shape (n_movies, n_movies)
    np.fill_diagonal(intersect_count, 0)    # remove self-match

    # Compute top-K recommendations
    top_k_idx = np.argpartition(-matrix, recom_n, axis=1)[:, :recom_n]  # fast top-K indices
    # Sort top-K
    row_idx = np.arange(n_movies)[:, None]
    top_k_idx = top_k_idx[np.arange(n_movies)[:, None], np.argsort(-matrix[row_idx, top_k_idx], axis=1)]

    # Compute metrics
    precisions = []
    hit_rates = []
    ap_list = []
    ndcg_list = []

    for i in range(n_movies):
        gt = np.where(intersect_count[i] > 0)[0]  # indices with shared attributes
        top_k = top_k_idx[i]
        hits = np.isin(top_k, gt)
        num_hits = hits.sum()

        # Precision@K
        precisions.append(num_hits / recom_n)
        # HitRate@K
        hit_rates.append(1.0 if num_hits > 0 else 0.0)
        # MAP@K
        if num_hits > 0:
            rel_positions = np.where(hits)[0] + 1
            ap = (np.arange(1, len(rel_positions)+1) / rel_positions).sum() / min(len(gt), recom_n)
        else:
            ap = 0.0
        ap_list.append(ap)
        # NDCG@K
        if num_hits > 0:
            dcg = (1 / np.log2(np.where(hits)[0]+2)).sum()
            idcg = (1 / np.log2(np.arange(1, min(len(gt), recom_n)+1)+1)).sum()
            ndcg_list.append(dcg / idcg)
        else:
            ndcg_list.append(0.0)

    # Prepare DataFrame
    metrics = ['Precision@K', 'HitRate@K', 'MAP@K', 'NDCG@K']
    scores = [np.mean(precisions), np.mean(hit_rates), np.mean(ap_list), np.mean(ndcg_list)]

    return pd.DataFrame({'Metric': metrics, 'Score': scores})



