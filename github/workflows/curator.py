# curator.py
# Curadoria ativa (inspirada em ActiveRAG): utilidade, novidade, risco
from __future__ import annotations
import sqlite3, json
from typing import Dict, Any
from memory_store import connect, embed, most_similar

def curator_check(text: str, con: sqlite3.Connection = None) -> Dict[str,Any]:
    close = []
    own = con or connect()
    vec = embed(text)
    for nid, score in most_similar(own, vec, top_k=5):
        close.append({"id": nid, "score": round(score, 4)})
    # heurísticas simples:
    utility = min(1.0, max(0.0, len(text) / 400.0))           # mais longo = mais informativo (grosseiro)
    novelty = 1.0 - max([c["score"] for c in close] + [0.0])  # quanto menos similar, mais novo
    risk = 0.0
    if "http://" in text or "https://" in text: risk += 0.1   # URLs às vezes são ruído
    if len(text) < 20: risk += 0.2                            # muito curto
    decision = "accommodate" if novelty > 0.4 and utility > 0.3 else "assimilate"
    return {"utility": round(utility,3), "novelty": round(novelty,3), "risk": round(risk,3),
            "closest": close, "decision": decision}