
# tests/_metrics.py
def precision_at_k(relevant_ids, retrieved_ids, k=None):
    if k is None: k = len(retrieved_ids)
    rel = set(relevant_ids)
    got = retrieved_ids[:k]
    if not got: return 0.0
    hit = sum(1 for x in got if x in rel)
    return hit / len(got)
