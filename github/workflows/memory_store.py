# memory_store.py
# Camada de memória (grafo leve em SQLite) + utilidades
from __future__ import annotations
import sqlite3, json, time, math, hashlib
from typing import List, Dict, Any, Tuple, Optional

DB_PATH = "memory_store.sqlite"

# --- Embedding (stub): troque por uma real quando quiser ---
def embed(text: str, dim: int = 64) -> List[float]:
    # Gera vetor determinístico a partir de hash (apenas para protótipo)
    h = hashlib.sha256(text.encode("utf-8")).digest()
    # repete bytes até ter 'dim' e normaliza
    vals = [(b - 128) / 128.0 for b in (h * ((dim // len(h)) + 1))[:dim]]
    # normaliza para unit norm
    n = math.sqrt(sum(v*v for v in vals)) or 1.0
    return [v / n for v in vals]

def cos(a: List[float], b: List[float]) -> float:
    return sum(x*y for x,y in zip(a,b))

def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    ensure_schema(con)
    return con

def ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript("""
    CREATE TABLE IF NOT EXISTS nodes(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      text TEXT NOT NULL,
      embedding TEXT NOT NULL, -- JSON array
      ts REAL NOT NULL DEFAULT (strftime('%s','now')),
      source TEXT DEFAULT NULL,
      meta   TEXT DEFAULT NULL
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_nodes_text ON nodes(text);

    CREATE TABLE IF NOT EXISTS edges(
      src INTEGER NOT NULL,
      dst INTEGER NOT NULL,
      rel TEXT NOT NULL,
      weight REAL NOT NULL DEFAULT 1.0,
      UNIQUE(src,dst,rel)
    );

    CREATE TABLE IF NOT EXISTS experiences(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      objective TEXT,
      step TEXT,
      tool TEXT,
      input TEXT,
      output TEXT,
      ok INTEGER,
      ts REAL NOT NULL DEFAULT (strftime('%s','now'))
    );
    """)
    con.commit()

def upsert_memory(con: sqlite3.Connection, text: str, source: str = None, meta: Dict[str,Any] = None,
                  relate_top_k: int = 3, relate_min_cos: float = 0.55) -> int:
    # tenta achar id existente
    cur = con.execute("SELECT id FROM nodes WHERE text=?", (text,))
    row = cur.fetchone()
    if row:
        return row[0]
    vec = embed(text)
    emb_json = json.dumps(vec)
    con.execute("INSERT INTO nodes(text, embedding, source, meta) VALUES(?,?,?,?)",
                (text, emb_json, source, json.dumps(meta or {})))
    nid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    # cria arestas "related" com os mais próximos
    rels = most_similar(con, vec, top_k=relate_top_k)
    for other_id, score in rels:
        if score < relate_min_cos: 
            continue
        con.execute("INSERT OR IGNORE INTO edges(src,dst,rel,weight) VALUES(?,?,?,?)",
                    (nid, other_id, "related", score))
        con.execute("INSERT OR IGNORE INTO edges(src,dst,rel,weight) VALUES(?,?,?,?)",
                    (other_id, nid, "related", score))
    con.commit()
    return nid

def most_similar(con: sqlite3.Connection, vec: List[float], top_k: int = 5) -> List[Tuple[int,float]]:
    rows = con.execute("SELECT id, embedding FROM nodes").fetchall()
    scored = []
    for nid, emb_json in rows:
        v = json.loads(emb_json)
        scored.append((nid, cos(vec, v)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]

def search_memory(con: sqlite3.Connection, query: str, top_k: int = 5, expand_hops: int = 1) -> Dict[str,Any]:
    qvec = embed(query)
    hits = most_similar(con, qvec, top_k=top_k)
    ids = {nid for nid,_ in hits}
    # expande vizinhança 1 salto
    frontier = set(ids)
    for _ in range(expand_hops):
        if not frontier: break
        new_ids = set()
        for nid in frontier:
            cur = con.execute("SELECT dst FROM edges WHERE src=? AND rel='related'", (nid,))
            new_ids.update([r[0] for r in cur.fetchall()])
        frontier = new_ids - ids
        ids |= new_ids
    # coleta nós
    nodes = []
    for nid in ids:
        nrow = con.execute("SELECT id, text, embedding, ts, source, meta FROM nodes WHERE id=?", (nid,)).fetchone()
        if not nrow: continue
        score = cos(qvec, json.loads(nrow[2]))
        nodes.append({
            "id": nrow[0], "text": nrow[1], "score": round(score, 4),
            "ts": nrow[3], "source": nrow[4], "meta": json.loads(nrow[5] or "{}")
        })
    nodes.sort(key=lambda d: d["score"], reverse=True)
    # arestas relevantes
    edges = con.execute(
        f"SELECT src,dst,rel,weight FROM edges WHERE src IN ({','.join('?'*len(ids))})",
        tuple(ids)
    ).fetchall() if ids else []
    return {"query": query, "hits": hits, "nodes": nodes, "edges": [{"src":a,"dst":b,"rel":r,"w":w} for a,b,r,w in edges]}