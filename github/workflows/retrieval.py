# retrieval.py
# Recuperação híbrida: embedding + vizinhança no grafo + reforço temporal
from __future__ import annotations
import time, sqlite3
from typing import Dict, Any
from memory_store import connect, search_memory

def hybrid_retrieve(query: str, top_k: int = 6, hops: int = 1, recency_boost: float = 0.15,
                    con: sqlite3.Connection = None) -> Dict[str,Any]:
    own = con or connect()
    res = search_memory(own, query, top_k=top_k, expand_hops=hops)
    now = time.time()
    for n in res["nodes"]:
        age_d = max(1.0, (now - n["ts"]) / 86400.0)
        n["score"] = round(n["score"] + recency_boost / age_d, 4)
    res["nodes"].sort(key=lambda d: d["score"], reverse=True)
    return res